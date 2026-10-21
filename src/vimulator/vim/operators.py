"""Operators (`d`, `c`, `y`) applied over a range, and `p`/`P`."""

from __future__ import annotations

from dataclasses import dataclass

from vimulator.vim.buffer import Buffer, Pos
from vimulator.vim.cursor import Cursor, resolve_want
from vimulator.vim.motions import MotionKind, MotionResult
from vimulator.vim.registers import Register


@dataclass(frozen=True, slots=True)
class Range:
    """What an operator acts on. For charwise ranges `end` is inclusive or exclusive per
    `kind`; for linewise ranges only the rows matter."""

    start: Pos
    end: Pos
    kind: MotionKind

    @property
    def linewise(self) -> bool:
        return self.kind is MotionKind.LINEWISE

    def end_exclusive(self, buf: Buffer) -> Pos:
        r, c = self.end
        if self.kind is MotionKind.INCLUSIVE:
            return (r, min(c + 1, len(buf.line(r))))
        return self.end

    def rows(self) -> tuple[int, int]:
        return self.start[0], self.end[0]


def build_range(buf: Buffer, cur: Cursor, res: MotionResult) -> Range:
    """Turn a motion result into an operator range, applying Vim's `exclusive-linewise`
    rule: an exclusive motion that ends in column 0 of a later line stops at the end of the
    previous line instead, and becomes linewise when it started in the indent."""
    a: Pos = (cur.row, cur.col)
    b: Pos = (res.row, res.col)
    start, end = (a, b) if a <= b else (b, a)
    kind = res.kind
    if kind is MotionKind.LINEWISE:
        return Range(start, end, kind)
    if kind is MotionKind.EXCLUSIVE and end[1] == 0 and end[0] > start[0]:
        end_row = end[0] - 1
        in_indent = buf.line(start[0])[: start[1]].strip(" \t") == ""
        if in_indent:
            return Range(start, (end_row, 0), MotionKind.LINEWISE)
        n = len(buf.line(end_row))
        if n:
            return Range(start, (end_row, n - 1), MotionKind.INCLUSIVE)
        return Range(start, (end_row, 0), MotionKind.EXCLUSIVE)
    return Range(start, end, kind)


def line_range(buf: Buffer, row: int, count: int) -> Range:
    return Range((row, 0), (min(row + count - 1, buf.last_row), 0), MotionKind.LINEWISE)


@dataclass(frozen=True, slots=True)
class OpResult:
    register: Register | None
    enter_insert: bool = False


def apply(op: str, buf: Buffer, cur: Cursor, rng: Range) -> OpResult:
    """Apply operator `op` over `rng`, moving the cursor as Vim would. The caller handles
    undo snapshots and mode changes."""
    if rng.linewise:
        r1, r2 = rng.rows()
        lines = buf.lines[r1 : r2 + 1]
        reg = Register("\n".join(lines), linewise=True)
        if op == "y":
            cur.set(rng.start[0], rng.start[1], cur.want_col)
            return OpResult(reg)
        if op == "d":
            buf.delete_lines(r1, r2 - r1 + 1)
            row = min(r1, buf.last_row)
            # Neovim default: 'nostartofline', so the column follows want_col.
            cur.set(row, resolve_want(buf, row, cur.want_col), cur.want_col)
            return OpResult(reg)
        # change: replace the lines with one line carrying the indent (autoindent).
        indent = buf.indent(r1)
        buf.delete_lines(r1, r2 - r1 + 1)
        if buf.lines == [""] and r1 == 0:
            buf.lines[0] = indent
        else:
            buf.insert_lines(r1, [indent])
        cur.set(r1, len(indent))
        return OpResult(reg, enter_insert=True)

    start = rng.start
    end = rng.end_exclusive(buf)
    if end <= start:
        return OpResult(None)
    text = buf.get_text(start, end)
    reg = Register(text, linewise=False)
    if op == "y":
        cur.set(start[0], start[1])
        return OpResult(reg)
    buf.delete_range(start, end)
    cur.set(start[0], start[1])
    return OpResult(reg, enter_insert=(op == "c"))


def put(buf: Buffer, cur: Cursor, reg: Register, after: bool, count: int = 1) -> None:
    if reg.linewise:
        at = cur.row + 1 if after else cur.row
        buf.insert_lines(at, reg.lines * count)
        cur.set(at, buf.first_nonblank(at))
        return
    text = reg.text * count
    row, col = cur.row, cur.col
    if after and len(buf.line(row)) > 0:
        col += 1
    buf.insert_multiline(row, col, text)
    if "\n" in text:
        cur.set(row, col)
    else:
        cur.set(row, col + len(text) - 1)
