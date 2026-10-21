"""A text buffer: a list of lines, never empty, no embedded newlines."""

from __future__ import annotations

from collections.abc import Iterable

Pos = tuple[int, int]


class Buffer:
    __slots__ = ("lines",)

    def __init__(self, lines: Iterable[str] | None = None) -> None:
        self.lines: list[str] = list(lines) if lines is not None else []
        if not self.lines:
            self.lines = [""]
        for line in self.lines:
            if "\n" in line:
                raise ValueError("buffer lines cannot contain newlines")

    def copy(self) -> Buffer:
        return Buffer(self.lines)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Buffer):
            return self.lines == other.lines
        return NotImplemented

    def __repr__(self) -> str:
        return f"Buffer({self.lines!r})"

    @property
    def last_row(self) -> int:
        return len(self.lines) - 1

    def line(self, row: int) -> str:
        return self.lines[row]

    def first_nonblank(self, row: int) -> int:
        """Column of the first non-blank, or the last column if the line is all blank."""
        line = self.lines[row]
        stripped = line.lstrip(" \t")
        if not stripped:
            return max(0, len(line) - 1)
        return len(line) - len(stripped)

    def indent(self, row: int) -> str:
        line = self.lines[row]
        return line[: len(line) - len(line.lstrip(" \t"))]

    # --- single-line edits -------------------------------------------------

    def insert_text(self, row: int, col: int, text: str) -> None:
        if "\n" in text:
            raise ValueError("use insert_lines or split_line for newlines")
        line = self.lines[row]
        self.lines[row] = line[:col] + text + line[col:]

    def delete_text(self, row: int, col: int, count: int) -> str:
        line = self.lines[row]
        removed = line[col : col + count]
        self.lines[row] = line[:col] + line[col + count :]
        return removed

    def replace_text(self, row: int, col: int, text: str) -> None:
        line = self.lines[row]
        self.lines[row] = line[:col] + text + line[col + len(text) :]

    # --- line edits --------------------------------------------------------

    def split_line(self, row: int, col: int) -> None:
        line = self.lines[row]
        self.lines[row : row + 1] = [line[:col], line[col:]]

    def join_with_next(self, row: int) -> None:
        """Append line `row + 1` to line `row` with no separator."""
        self.lines[row : row + 2] = [self.lines[row] + self.lines[row + 1]]

    def insert_lines(self, at: int, new_lines: Iterable[str]) -> None:
        self.lines[at:at] = list(new_lines)

    def delete_lines(self, start: int, count: int) -> list[str]:
        removed = self.lines[start : start + count]
        del self.lines[start : start + count]
        if not self.lines:
            self.lines = [""]
        return removed

    # --- charwise ranges, end exclusive -----------------------------------

    def get_text(self, start: Pos, end: Pos) -> str:
        (r1, c1), (r2, c2) = start, end
        if r1 == r2:
            return self.lines[r1][c1:c2]
        parts = [self.lines[r1][c1:]]
        parts.extend(self.lines[r1 + 1 : r2])
        parts.append(self.lines[r2][:c2])
        return "\n".join(parts)

    def delete_range(self, start: Pos, end: Pos) -> str:
        text = self.get_text(start, end)
        (r1, c1), (r2, c2) = start, end
        self.lines[r1 : r2 + 1] = [self.lines[r1][:c1] + self.lines[r2][c2:]]
        return text

    def insert_multiline(self, row: int, col: int, text: str) -> None:
        pieces = text.split("\n")
        line = self.lines[row]
        head, tail = line[:col], line[col:]
        if len(pieces) == 1:
            self.lines[row] = head + text + tail
            return
        new = [head + pieces[0], *pieces[1:-1], pieces[-1] + tail]
        self.lines[row : row + 1] = new
