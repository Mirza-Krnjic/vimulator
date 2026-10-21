"""The Editor facade: feed keys, get Vim behaviour, no pygame."""

from __future__ import annotations

from dataclasses import dataclass, field

from vimulator.vim import operators
from vimulator.vim.buffer import Buffer, Pos
from vimulator.vim.cursor import END, Cursor, clamp
from vimulator.vim.keys import Key
from vimulator.vim.modes import Mode
from vimulator.vim.motions import KEEP, MotionKind, move
from vimulator.vim.operators import Range
from vimulator.vim.parser import Command, CommandSpec, Invalid, Parser, Pending
from vimulator.vim.registers import Register


@dataclass(frozen=True, slots=True)
class Snapshot:
    lines: tuple[str, ...]
    row: int
    col: int
    want_col: int


@dataclass(frozen=True, slots=True)
class Highlight:
    """A range in pre-change coordinates, for the HUD to flash before the edit lands."""

    start: Pos
    end: Pos  # inclusive for charwise
    linewise: bool


@dataclass(slots=True)
class FeedResult:
    description: str = ""
    pending: bool = False
    changed: bool = False
    invalid: bool = False
    highlight: Highlight | None = None
    before: list[str] = field(default_factory=list)
    submitted: bool = False  # :wq, :x
    quit: bool = False  # :q, :q!
    restart: bool = False  # :e!


class Editor:
    def __init__(
        self, lines: list[str] | None = None, cursor: Pos = (0, 0), insert: bool = False
    ) -> None:
        self.buffer = Buffer(lines)
        self.cursor = Cursor(cursor[0], cursor[1], cursor[1])
        clamp(self.cursor, self.buffer, insert=insert)
        self.mode = Mode.NORMAL
        self.register: Register | None = None
        self.parser = Parser()
        self.undo_stack: list[Snapshot] = []
        self.redo_stack: list[Snapshot] = []
        self.keys: list[Key] = []
        self.cmdline = ""
        self._insert_snapshot: Snapshot | None = None
        self._autoindent_pending = False
        if insert:
            self.enter_insert()

    # --- public ------------------------------------------------------------------

    @property
    def keystrokes(self) -> int:
        return len(self.keys)

    @property
    def lines(self) -> list[str]:
        return self.buffer.lines

    def enter_insert(self) -> None:
        """Start in Insert mode (levels that begin there)."""
        self.mode = Mode.INSERT
        self._insert_snapshot = self._snapshot()

    def feed(self, key: Key) -> FeedResult:
        self.keys.append(key)
        if self.mode is Mode.INSERT:
            return self._feed_insert(key)
        if self.mode is Mode.CMDLINE:
            return self._feed_cmdline(key)
        return self._feed_normal(key)

    def feed_all(self, keys: list[Key]) -> FeedResult:
        result = FeedResult()
        for k in keys:
            result = self.feed(k)
        return result

    # --- normal mode -------------------------------------------------------------

    def _feed_normal(self, key: Key) -> FeedResult:
        parsed = self.parser.feed(key)
        if isinstance(parsed, Pending):
            return FeedResult(description=parsed.description, pending=True)
        if isinstance(parsed, Invalid):
            return FeedResult(invalid=True)
        assert isinstance(parsed, Command)
        result = self._execute(parsed.spec)
        result.description = parsed.description
        if self.mode is Mode.NORMAL:
            clamp(self.cursor, self.buffer, insert=False)
        return result

    def _execute(self, spec: CommandSpec) -> FeedResult:
        match spec.kind:
            case "motion":
                return self._do_motion(spec.key, spec.count)
            case "operator_motion":
                assert spec.operator is not None
                return self._do_operator_motion(spec.operator, spec.key, spec.count)
            case "operator_line":
                assert spec.operator is not None
                return self._do_operator_line(spec.operator, spec.count)
            case "replace":
                assert spec.char is not None
                return self._do_replace(spec.char, spec.count)
            case "redo":
                return self._do_redo()
            case "simple":
                return self._do_simple(spec.key, spec.count)
        return FeedResult(invalid=True)

    def _do_motion(self, key: str, count: int) -> FeedResult:
        res = move(key, self.buffer, self.cursor, count, None)
        if res is None:
            return FeedResult()
        self._apply_motion_cursor(res)
        return FeedResult()

    def _apply_motion_cursor(self, res: object) -> None:
        from vimulator.vim.motions import MotionResult

        assert isinstance(res, MotionResult)
        if res.want_col == KEEP:
            want = self.cursor.want_col
        elif res.want_col == END:
            want = END
        else:
            want = res.col
        self.cursor.set(res.row, res.col, want)

    def _do_operator_motion(self, op: str, key: str, count: int) -> FeedResult:
        res = move(key, self.buffer, self.cursor, count, op)
        if res is None:
            return FeedResult()
        rng = operators.build_range(self.buffer, self.cursor, res)
        return self._apply_operator(op, rng)

    def _do_operator_line(self, op: str, count: int) -> FeedResult:
        if count > 1 and self.cursor.row == self.buffer.last_row:
            return FeedResult()  # Vim beeps: `2dd` on the last line does nothing
        rng = operators.line_range(self.buffer, self.cursor.row, count)
        return self._apply_operator(op, rng)

    def _apply_operator(self, op: str, rng: Range) -> FeedResult:
        before = list(self.buffer.lines)
        highlight = Highlight(rng.start, rng.end, rng.linewise)
        if rng.kind is not MotionKind.LINEWISE and rng.end_exclusive(self.buffer) <= rng.start:
            # Empty range: `d` and `y` do nothing, `c` still enters Insert mode (Vim does
            # the same for `c$` on an empty line).
            if op == "c":
                self.cursor.set(rng.start[0], rng.start[1])
                self._start_insert()
            return FeedResult()
        if op != "y":
            self._push_undo()
        out = operators.apply(op, self.buffer, self.cursor, rng)
        if out.register is not None:
            self.register = out.register
        if out.enter_insert:
            self._autoindent_pending = rng.linewise and self.cursor.col > 0
            self._start_insert(snapshot_already_taken=True)
        return FeedResult(changed=op != "y", highlight=highlight, before=before)

    def _do_replace(self, char: str, count: int) -> FeedResult:
        row, col = self.cursor.row, self.cursor.col
        if col + count > len(self.buffer.line(row)):
            return FeedResult()
        before = list(self.buffer.lines)
        self._push_undo()
        self.buffer.replace_text(row, col, char * count)
        self.cursor.set(row, col + count - 1)
        return FeedResult(
            changed=True,
            highlight=Highlight((row, col), (row, col + count - 1), False),
            before=before,
        )

    def _do_simple(self, key: str, count: int) -> FeedResult:
        cur = self.cursor
        match key:
            case "x":
                return self._do_operator_motion("d", "l", count)
            case "X":
                return self._do_operator_motion("d", "h", count)
            case "s":
                return self._do_operator_motion("c", "l", count)
            case "S":
                return self._do_operator_line("c", count)
            case "C":
                return self._do_operator_motion("c", "$", count)
            case "D":
                return self._do_operator_motion("d", "$", count)
            case "p" | "P":
                if self.register is None:
                    return FeedResult()
                before = list(self.buffer.lines)
                self._push_undo()
                operators.put(self.buffer, cur, self.register, after=(key == "p"), count=count)
                return FeedResult(changed=True, before=before)
            case "u":
                return self._do_undo()
            case "i":
                self._start_insert()
            case "a":
                if len(self.buffer.line(cur.row)) > 0:
                    cur.set(cur.row, cur.col + 1)
                self._start_insert()
            case "A":
                cur.set(cur.row, len(self.buffer.line(cur.row)))
                self._start_insert()
            case "I":
                line = self.buffer.line(cur.row)
                cur.set(cur.row, len(line) - len(line.lstrip(" \t")))
                self._start_insert()
            case "o" | "O":
                before = list(self.buffer.lines)
                self._push_undo()
                indent = self.buffer.indent(cur.row)
                at = cur.row + 1 if key == "o" else cur.row
                self.buffer.insert_lines(at, [indent])
                cur.set(at, len(indent))
                self._autoindent_pending = len(indent) > 0
                self._start_insert(snapshot_already_taken=True)
                return FeedResult(changed=True, before=before)
            case ":":
                self.mode = Mode.CMDLINE
                self.cmdline = ""
        return FeedResult()

    # --- insert mode -------------------------------------------------------------

    def _start_insert(self, snapshot_already_taken: bool = False) -> None:
        self.mode = Mode.INSERT
        if snapshot_already_taken:
            # The undo entry for this change is already on the stack; the insert session
            # extends it, so remember that there is nothing to discard on Esc.
            self._insert_snapshot = None
        else:
            self._insert_snapshot = self._snapshot()

    def _feed_insert(self, key: Key) -> FeedResult:
        cur = self.cursor
        buf = self.buffer
        if key.name == "esc":
            if self._autoindent_pending and buf.line(cur.row).strip(" \t") == "":
                buf.lines[cur.row] = ""
                cur.set(cur.row, 0)
            self._autoindent_pending = False
            snap = self._insert_snapshot
            self._insert_snapshot = None
            if snap is not None and tuple(buf.lines) != snap.lines:
                self.redo_stack.clear()
                self.undo_stack.append(snap)
            self.mode = Mode.NORMAL
            self.parser.reset()
            if cur.col > 0:
                cur.set(cur.row, cur.col - 1)
            clamp(cur, buf, insert=False)
            return FeedResult(changed=True)
        if key.ctrl:
            return FeedResult(invalid=True)
        if key.name == "enter":
            if self._autoindent_pending and buf.line(cur.row).strip(" \t") == "":
                buf.lines[cur.row] = ""
                cur.set(cur.row, 0)
            indent = buf.indent(cur.row)
            tail = buf.line(cur.row)[cur.col :]
            buf.split_line(cur.row, cur.col)
            buf.lines[cur.row + 1] = indent + tail
            cur.set(cur.row + 1, len(indent))
            self._autoindent_pending = len(indent) > 0 and tail == ""
            return FeedResult(changed=True)
        if key.name == "backspace":
            if cur.col > 0:
                buf.delete_text(cur.row, cur.col - 1, 1)
                cur.set(cur.row, cur.col - 1)
            elif cur.row > 0:
                new_col = len(buf.line(cur.row - 1))
                buf.join_with_next(cur.row - 1)
                cur.set(cur.row - 1, new_col)
            return FeedResult(changed=True)
        assert key.char is not None
        buf.insert_text(cur.row, cur.col, key.char)
        cur.set(cur.row, cur.col + 1)
        self._autoindent_pending = False
        return FeedResult(changed=True)

    # --- command line ------------------------------------------------------------

    def _feed_cmdline(self, key: Key) -> FeedResult:
        if key.name == "esc":
            self.mode = Mode.NORMAL
            self.cmdline = ""
            return FeedResult()
        if key.name == "backspace":
            if self.cmdline:
                self.cmdline = self.cmdline[:-1]
            else:
                self.mode = Mode.NORMAL
            return FeedResult()
        if key.name == "enter":
            cmd = self.cmdline.strip()
            self.cmdline = ""
            self.mode = Mode.NORMAL
            if cmd in {"wq", "x", "wqa", "xa"}:
                return FeedResult(submitted=True, description="write and quit")
            if cmd in {"q", "q!", "qa", "qa!"}:
                return FeedResult(quit=True, description="quit the level")
            if cmd in {"e", "e!"}:
                return FeedResult(restart=True, description="reload the level")
            if cmd == "w":
                return FeedResult(description="write")
            return FeedResult(invalid=True)
        if key.is_printable:
            assert key.char is not None
            self.cmdline += key.char
        return FeedResult(description="command line ...", pending=True)

    # --- undo ----------------------------------------------------------------------

    def _snapshot(self) -> Snapshot:
        c = self.cursor
        return Snapshot(tuple(self.buffer.lines), c.row, c.col, c.want_col)

    def _restore(self, snap: Snapshot) -> None:
        self.buffer.lines = list(snap.lines)
        self.cursor.set(snap.row, snap.col, snap.want_col)
        clamp(self.cursor, self.buffer, insert=False)

    def _push_undo(self) -> None:
        self.undo_stack.append(self._snapshot())
        self.redo_stack.clear()

    def _do_undo(self) -> FeedResult:
        if not self.undo_stack:
            return FeedResult()
        before = list(self.buffer.lines)
        self.redo_stack.append(self._snapshot())
        self._restore(self.undo_stack.pop())
        return FeedResult(changed=True, before=before)

    def _do_redo(self) -> FeedResult:
        if not self.redo_stack:
            return FeedResult()
        before = list(self.buffer.lines)
        self.undo_stack.append(self._snapshot())
        self._restore(self.redo_stack.pop())
        return FeedResult(changed=True, before=before)
