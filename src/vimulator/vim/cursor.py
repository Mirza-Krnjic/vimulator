"""Cursor position plus the column the cursor wants to be in after vertical moves."""

from __future__ import annotations

from dataclasses import dataclass

from vimulator.vim.buffer import Buffer

END = -1  # want_col value meaning "end of line", set by `$`


@dataclass(slots=True)
class Cursor:
    row: int = 0
    col: int = 0
    want_col: int = 0

    @property
    def pos(self) -> tuple[int, int]:
        return (self.row, self.col)

    def set(self, row: int, col: int, want_col: int | None = None) -> None:
        self.row = row
        self.col = col
        self.want_col = col if want_col is None else want_col


def max_col(buf: Buffer, row: int, insert: bool) -> int:
    n = len(buf.line(row))
    return n if insert else max(0, n - 1)


def resolve_want(buf: Buffer, row: int, want_col: int, insert: bool = False) -> int:
    limit = max_col(buf, row, insert)
    if want_col == END:
        return limit
    return min(want_col, limit)


def clamp(cur: Cursor, buf: Buffer, insert: bool) -> None:
    cur.row = min(max(cur.row, 0), buf.last_row)
    cur.col = min(max(cur.col, 0), max_col(buf, cur.row, insert))
