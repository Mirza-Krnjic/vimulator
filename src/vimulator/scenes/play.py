"""The level scene: buffer, goal, grammar HUD, keystroke counter."""

from __future__ import annotations

import pygame

from vimulator import config
from vimulator.levels import Level, start_editor
from vimulator.scenes import Scene
from vimulator.ui import hud
from vimulator.ui.text_grid import Cell, wrap_text
from vimulator.vim.editor import Highlight
from vimulator.vim.keys import Key
from vimulator.vim.modes import Mode


def highlight_cells(lines: list[str], hl: Highlight) -> set[Cell]:
    cells: set[Cell] = set()
    (r1, c1), (r2, c2) = hl.start, hl.end
    for row in range(r1, r2 + 1):
        if row >= len(lines):
            break
        n = max(1, len(lines[row]))
        if hl.linewise:
            lo, hi = 0, n - 1
        else:
            lo = c1 if row == r1 else 0
            hi = c2 if row == r2 else n - 1
        for col in range(lo, min(hi, n - 1) + 1):
            cells.add((row, col))
    return cells


class PlayScene(Scene):
    def __init__(self, app, level: Level) -> None:
        super().__init__(app)
        self.level = level
        self.reset()

    def reset(self) -> None:
        self.editor = start_editor(self.level)
        self.description = ""
        self.pending = False
        self.flash_lines: list[str] | None = None
        self.flash_cells: set[Cell] = set()
        self.flash_left = 0.0
        self.done = False

    # --- input ------------------------------------------------------------------

    def handle_key(self, key: Key) -> None:
        if self.done:
            return
        result = self.editor.feed(key)
        if result.quit:
            self.app.pop_to_select(self.level)
            return
        if result.restart:
            self.reset()
            return
        if self.editor.mode is Mode.INSERT:
            self.description, self.pending = "", False
        elif result.invalid:
            self.description, self.pending = "", False
        elif result.description or result.pending:
            self.description, self.pending = result.description, result.pending
        if result.highlight is not None and result.before:
            self.flash_lines = result.before
            self.flash_cells = highlight_cells(result.before, result.highlight)
            self.flash_left = config.HIGHLIGHT_SECONDS
        if self._is_complete(result.submitted):
            self.done = True
            from vimulator.scenes.results import ResultsScene

            self.app.push(ResultsScene(self.app, self.level, self.editor))

    def _is_complete(self, submitted: bool) -> bool:
        ed = self.editor
        if ed.mode is not Mode.NORMAL or ed.lines != list(self.level.goal):
            return False
        if self.level.goal_cursor is not None and ed.cursor.pos != self.level.goal_cursor:
            return False
        if self.level.requires_submit and not submitted:
            return False
        return True

    def update(self, dt: float) -> None:
        if self.flash_left > 0:
            self.flash_left -= dt
            if self.flash_left <= 0:
                self.flash_lines = None
                self.flash_cells = set()

    # --- drawing ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        fonts, grid, m = self.app.fonts, self.app.grid, config.MARGIN
        level, ed = self.level, self.editor
        width = config.WINDOW_WIDTH

        # Header
        head = fonts.hud.render(f"{level.id}  {level.title}", True, config.FOREGROUND)
        surface.blit(head, (m, m - 4))
        hud.draw_mode_badge(surface, fonts.hud, ed.mode.value, width - m, m - 4)

        # Grammar strip
        gy = config.HEADER_HEIGHT
        hud.draw_grammar(surface, fonts.hud, self.description, m, gy, self.pending)

        # Panels
        top = config.HEADER_HEIGHT + config.GRAMMAR_HEIGHT + 8
        bottom = config.WINDOW_HEIGHT - config.FOOTER_HEIGHT
        gap = 16
        panel_w = (width - 2 * m - gap) // 2
        buf_rect = pygame.Rect(m, top, panel_w, bottom - top)
        goal_rect = pygame.Rect(m + panel_w + gap, top, panel_w, bottom - top)
        buf_inner = hud.draw_panel(surface, buf_rect, "buffer", fonts.small)
        goal_inner = hud.draw_panel(surface, goal_rect, "goal", fonts.small)
        max_rows = buf_inner.h // grid.cell_h

        lines = self.flash_lines if self.flash_lines is not None else ed.lines
        insert = ed.mode is Mode.INSERT
        grid.draw_lines(
            surface,
            buf_inner.topleft,
            lines,
            config.FOREGROUND,
            cursor=ed.cursor.pos if self.flash_lines is None else None,
            cursor_color=config.CURSOR_INSERT if insert else config.CURSOR_NORMAL,
            cursor_bar=insert,
            highlight=self.flash_cells or None,
            highlight_color=config.HIGHLIGHT,
            highlight_text=config.BACKGROUND,
            marker=level.goal_cursor,
            marker_color=config.GOAL_CURSOR,
            max_rows=max_rows,
        )
        if ed.mode is Mode.CMDLINE:
            grid.draw_text(
                surface, buf_inner.x, buf_inner.bottom - grid.cell_h, ":" + ed.cmdline, config.PEACH
            )

        goal = list(level.goal)
        row_colors = {
            i: (config.MUTED if i < len(ed.lines) and ed.lines[i] == line else config.YELLOW)
            for i, line in enumerate(goal)
        }
        grid.draw_lines(
            surface,
            goal_inner.topleft,
            goal,
            config.MUTED,
            row_colors=row_colors,
            marker=level.goal_cursor,
            marker_color=config.GOAL_CURSOR,
            max_rows=max_rows,
        )

        # Footer: brief, hint, counter
        fy = bottom + 12
        brief = wrap_text(fonts.small, level.brief, width - 2 * m - 330)
        y = hud.draw_text_block(surface, fonts.small, brief, m, fy, config.FOREGROUND)
        if ed.keystrokes > level.par * config.HINT_AFTER_FACTOR and level.hint:
            hint = wrap_text(fonts.small, "hint: " + level.hint, width - 2 * m - 330)
            hud.draw_text_block(surface, fonts.small, hint, m, y + 4, config.MAUVE)
        hud.draw_counter(surface, fonts.hud, ed.keystrokes, level.par, width - m, fy)
        help_text = fonts.small.render(":q leave    :e! restart", True, config.PANEL_EDGE)
        surface.blit(help_text, (width - m - help_text.get_width(), fy + 40))
