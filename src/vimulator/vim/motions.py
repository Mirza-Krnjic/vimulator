"""Cursor motions with Vim semantics.

The word motions are a direct port of Vim's `fwd_word`, `bck_word` and `end_word`, including the
position "on the NUL past the end of the line" that those routines pass through. Each motion
returns where the cursor would land and whether the range it defines is exclusive, inclusive or
linewise, which is what operators need.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vimulator.vim.buffer import Buffer, Pos
from vimulator.vim.cursor import END, Cursor, resolve_want


class MotionKind(Enum):
    EXCLUSIVE = "exclusive"
    INCLUSIVE = "inclusive"
    LINEWISE = "linewise"


KEEP = -2  # want_col sentinel: keep the current want_col (vertical motions)


@dataclass(frozen=True, slots=True)
class MotionResult:
    row: int
    col: int
    kind: MotionKind
    want_col: int | None = None  # None: want_col becomes col; END or KEEP otherwise


MOTION_KEYS = frozenset("hjkl0^$wbe")


# --- character classes and position stepping (Vim's cls / inc / dec) -------------


def _cls(buf: Buffer, pos: Pos) -> int:
    row, col = pos
    line = buf.line(row)
    if col >= len(line):
        return 0
    c = line[col]
    if c in " \t":
        return 0
    if c.isalnum() or c == "_" or ord(c) >= 192:
        return 2
    return 1


def _inc(buf: Buffer, pos: Pos) -> tuple[Pos, int]:
    """Step forward. Returns (pos, code): 0 within line, 2 onto the NUL at end of line,
    1 onto the next line, -1 at end of buffer (pos unchanged)."""
    row, col = pos
    line = buf.line(row)
    if col < len(line):
        col += 1
        return (row, col), (0 if col < len(line) else 2)
    if row < buf.last_row:
        return (row + 1, 0), 1
    return pos, -1


def _dec(buf: Buffer, pos: Pos) -> tuple[Pos, int]:
    """Step backward. Returns (pos, code): 0 within line, 1 onto the NUL of the previous
    line, -1 at start of buffer (pos unchanged)."""
    row, col = pos
    if col > 0:
        return (row, col - 1), 0
    if row > 0:
        return (row - 1, len(buf.line(row - 1))), 1
    return pos, -1


def _is_empty_line(buf: Buffer, pos: Pos) -> bool:
    return pos[1] == 0 and buf.line(pos[0]) == ""


def _skip_chars(buf: Buffer, pos: Pos, cclass: int, forward: bool) -> tuple[Pos, bool]:
    """Skip over characters of class `cclass`. Returns (pos, hit_buffer_edge)."""
    step = _inc if forward else _dec
    while _cls(buf, pos) == cclass:
        pos, code = step(buf, pos)
        if code == -1:
            return pos, True
    return pos, False


def fwd_word(buf: Buffer, pos: Pos, count: int, eol: bool) -> tuple[Pos, bool]:
    """Vim's fwd_word. `eol` is true when an operator is pending: the motion then stops at
    the end of the line instead of continuing to the next word on the next line."""
    for i in range(count):
        last = i == count - 1
        sclass = _cls(buf, pos)
        last_line = pos[0] == buf.last_row
        pos, code = _inc(buf, pos)
        if code == -1 or (code >= 1 and last_line):
            return pos, False
        if code >= 1 and eol and last:
            return pos, True
        if sclass != 0:
            while _cls(buf, pos) == sclass:
                pos, code = _inc(buf, pos)
                if code == -1 or (code >= 1 and eol and last):
                    return pos, True
        while _cls(buf, pos) == 0:
            if _is_empty_line(buf, pos):
                break
            pos, code = _inc(buf, pos)
            if code == -1 or (code >= 1 and eol and last):
                return pos, True
    return pos, True


def bck_word(buf: Buffer, pos: Pos, count: int, stop: bool = False) -> tuple[Pos, bool]:
    """Vim's bck_word."""
    for _ in range(count):
        sclass = _cls(buf, pos)
        pos, code = _dec(buf, pos)
        if code == -1:
            return pos, False
        finished = False
        if not stop or sclass == _cls(buf, pos) or sclass == 0:
            while _cls(buf, pos) == 0:
                if _is_empty_line(buf, pos):
                    finished = True
                    break
                pos, code = _dec(buf, pos)
                if code == -1:
                    return pos, True
            if not finished:
                pos, hit = _skip_chars(buf, pos, _cls(buf, pos), forward=False)
                if hit:
                    return pos, True
        if not finished:
            pos, _ = _inc(buf, pos)
        stop = False
    return pos, True


def end_word(
    buf: Buffer, pos: Pos, count: int, stop: bool = False, empty: bool = False
) -> tuple[Pos, bool]:
    """Vim's end_word. `stop` is the `cw` special case (do not skip to the next word when
    already at the end of one)."""
    for _ in range(count):
        sclass = _cls(buf, pos)
        pos, code = _inc(buf, pos)
        if code == -1:
            return pos, False
        finished = False
        if _cls(buf, pos) == sclass and sclass != 0:
            pos, hit = _skip_chars(buf, pos, sclass, forward=True)
            if hit:
                return pos, False
        elif not stop or sclass == 0:
            while _cls(buf, pos) == 0:
                if empty and _is_empty_line(buf, pos):
                    finished = True
                    break
                pos, code = _inc(buf, pos)
                if code == -1:
                    return pos, False
            if not finished:
                pos, hit = _skip_chars(buf, pos, _cls(buf, pos), forward=True)
                if hit:
                    return pos, False
        if not finished:
            pos, _ = _dec(buf, pos)
        stop = False
    return pos, True


# --- the motion table ------------------------------------------------------------


def move(
    key: str, buf: Buffer, cur: Cursor, count: int, operator: str | None
) -> MotionResult | None:
    """Compute where motion `key` lands from `cur`. Returns None when the motion fails
    (nothing moves, a pending operator is cancelled)."""
    row, col = cur.row, cur.col
    line = buf.line(row)
    n = len(line)

    if key == "h":
        if col == 0:
            return None
        return MotionResult(row, max(0, col - count), MotionKind.EXCLUSIVE)

    if key == "l":
        if operator is None:
            if col >= n - 1:
                return None
            return MotionResult(row, min(col + count, n - 1), MotionKind.EXCLUSIVE)
        if n == 0:
            return None
        if col + count <= n - 1:
            return MotionResult(row, col + count, MotionKind.EXCLUSIVE)
        # Ran into the end of the line: Vim makes the motion inclusive so `x` and `dl`
        # still take the last character.
        return MotionResult(row, n - 1, MotionKind.INCLUSIVE)

    if key == "j":
        if row == buf.last_row:
            return None
        target = min(row + count, buf.last_row)
        return MotionResult(
            target, resolve_want(buf, target, cur.want_col), MotionKind.LINEWISE, KEEP
        )

    if key == "k":
        if row == 0:
            return None
        target = max(row - count, 0)
        return MotionResult(
            target, resolve_want(buf, target, cur.want_col), MotionKind.LINEWISE, KEEP
        )

    if key == "0":
        return MotionResult(row, 0, MotionKind.EXCLUSIVE)

    if key == "^":
        return MotionResult(row, buf.first_nonblank(row), MotionKind.EXCLUSIVE)

    if key == "$":
        if count > 1 and row == buf.last_row:
            return None
        target = min(row + count - 1, buf.last_row)
        return MotionResult(target, max(0, len(buf.line(target)) - 1), MotionKind.INCLUSIVE, END)

    if key in "wbe":
        return _word_motion(key, buf, cur, count, operator)

    return None


def _word_motion(
    key: str, buf: Buffer, cur: Cursor, count: int, operator: str | None
) -> MotionResult | None:
    start: Pos = (cur.row, cur.col)
    if key == "b":
        pos, ok = bck_word(buf, start, count)
        if not ok:
            return None
        return MotionResult(pos[0], pos[1], MotionKind.EXCLUSIVE)

    if key == "w" and operator == "c" and _cls(buf, start) != 0:
        # `cw` on a word behaves like `ce`.
        pos, ok = end_word(buf, start, count, stop=True)
        kind = MotionKind.INCLUSIVE
    elif key == "w":
        pos, ok = fwd_word(buf, start, count, eol=operator is not None)
        kind = MotionKind.EXCLUSIVE
    else:  # "e"
        pos, ok = end_word(buf, start, count)
        kind = MotionKind.INCLUSIVE

    # Vim's adjust_cursor: never leave the cursor on the NUL past the end of the line. With
    # an operator pending the range becomes inclusive so the last character is still taken.
    if pos > start:
        r, c = pos
        if c > 0 and c == len(buf.line(r)):
            pos = (r, c - 1)
            kind = MotionKind.INCLUSIVE
    if not ok and operator is None:
        return None
    return MotionResult(pos[0], pos[1], kind)
