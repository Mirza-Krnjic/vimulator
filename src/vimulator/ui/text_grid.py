"""A monospace text grid with a glyph cache, for drawing buffers and lists."""

from __future__ import annotations

from collections.abc import Iterable

import pygame

Color = tuple[int, int, int]
Cell = tuple[int, int]


class TextGrid:
    def __init__(self, font: pygame.font.Font) -> None:
        self.font = font
        self.cell_w = font.size("M")[0]
        self.cell_h = font.get_linesize()
        self._cache: dict[tuple[str, Color], pygame.Surface] = {}

    def glyph(self, ch: str, color: Color) -> pygame.Surface:
        key = (ch, color)
        surf = self._cache.get(key)
        if surf is None:
            surf = self.font.render(ch, True, color)
            self._cache[key] = surf
        return surf

    def draw_text(self, surface: pygame.Surface, x: int, y: int, text: str, color: Color) -> int:
        """Draw `text` starting at (x, y). Returns the x after the last glyph."""
        for ch in text:
            surface.blit(self.glyph(ch, color), (x, y))
            x += self.cell_w
        return x

    def draw_lines(
        self,
        surface: pygame.Surface,
        origin: tuple[int, int],
        lines: Iterable[str],
        color: Color,
        *,
        cursor: Cell | None = None,
        cursor_color: Color | None = None,
        cursor_bar: bool = False,
        highlight: set[Cell] | None = None,
        highlight_color: Color | None = None,
        highlight_text: Color | None = None,
        row_colors: dict[int, Color] | None = None,
        marker: Cell | None = None,
        marker_color: Color | None = None,
        max_rows: int | None = None,
    ) -> None:
        """Draw lines of text with optional cursor, highlighted cells and a target marker."""
        ox, oy = origin
        for row, line in enumerate(lines):
            if max_rows is not None and row >= max_rows:
                break
            y = oy + row * self.cell_h
            fg = row_colors.get(row, color) if row_colors else color
            cells = line if line else " "
            for col, ch in enumerate(cells):
                x = ox + col * self.cell_w
                in_highlight = highlight is not None and (row, col) in highlight
                is_cursor = cursor == (row, col) and not cursor_bar
                if in_highlight and highlight_color is not None:
                    pygame.draw.rect(surface, highlight_color, (x, y, self.cell_w, self.cell_h))
                    surface.blit(self.glyph(ch, highlight_text or fg), (x, y))
                elif is_cursor and cursor_color is not None:
                    pygame.draw.rect(surface, cursor_color, (x, y, self.cell_w, self.cell_h))
                    surface.blit(self.glyph(ch, (30, 30, 46)), (x, y))
                else:
                    surface.blit(self.glyph(ch, fg), (x, y))
            if cursor is not None and cursor[0] == row and cursor_bar and cursor_color is not None:
                x = ox + cursor[1] * self.cell_w
                pygame.draw.rect(surface, cursor_color, (x - 1, y, 2, self.cell_h))
            if marker is not None and marker[0] == row and marker_color is not None:
                x = ox + marker[1] * self.cell_w
                pygame.draw.rect(surface, marker_color, (x, y, self.cell_w, self.cell_h), 2)


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    """Greedy word wrap for proportional or monospace fonts."""
    lines: list[str] = []
    for paragraph in text.split("\n"):
        words = paragraph.split(" ")
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= max_width or not current:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines
