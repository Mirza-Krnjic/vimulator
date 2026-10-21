"""World tabs plus a level list. h/l pick a world, j/k pick a level, Enter plays, q quits."""

from __future__ import annotations

import pygame

from vimulator import config
from vimulator.scenes import Scene
from vimulator.ui import hud
from vimulator.ui.text_grid import wrap_text
from vimulator.vim.keys import Key


class LevelSelectScene(Scene):
    def __init__(self, app, world_index: int = 0, level_index: int = 0) -> None:
        super().__init__(app)
        self.world_index = world_index
        self.level_index = level_index

    @property
    def world(self):
        return self.app.worlds[self.world_index]

    def handle_key(self, key: Key) -> None:
        from vimulator.scenes.play import PlayScene

        if key.name == "enter":
            self.app.push(PlayScene(self.app, self.world.levels[self.level_index]))
            return
        if not key.is_printable:
            return
        match key.char:
            case "j":
                self.level_index = min(self.level_index + 1, len(self.world.levels) - 1)
            case "k":
                self.level_index = max(self.level_index - 1, 0)
            case "l":
                self.world_index = min(self.world_index + 1, len(self.app.worlds) - 1)
                self.level_index = 0
            case "h":
                self.world_index = max(self.world_index - 1, 0)
                self.level_index = 0
            case "q":
                self.app.quit()

    def draw(self, surface: pygame.Surface) -> None:
        fonts = self.app.fonts
        m = config.MARGIN
        title = fonts.title.render("VIMULATOR", True, config.FOREGROUND)
        surface.blit(title, (m, m))
        sub = fonts.small.render("a game for learning Vim", True, config.MUTED)
        surface.blit(
            sub, (m + title.get_width() + 16, m + title.get_height() - sub.get_height() - 6)
        )

        # World tabs
        y = m + title.get_height() + 18
        x = m
        for i, world in enumerate(self.app.worlds):
            selected = i == self.world_index
            text = f" {world.number}  {world.title} "
            label = fonts.small.render(text, True, config.BACKGROUND if selected else config.MUTED)
            rect = label.get_rect(topleft=(x, y))
            if selected:
                pygame.draw.rect(surface, config.ACCENT, rect.inflate(6, 6), border_radius=6)
            surface.blit(label, rect)
            x += rect.width + 14

        # Intro
        y += 40
        intro_lines = wrap_text(fonts.small, self.world.intro, config.WINDOW_WIDTH - 2 * m)
        y = hud.draw_text_block(surface, fonts.small, intro_lines, m, y, config.MUTED) + 12

        # Level list
        panel = pygame.Rect(m, y, config.WINDOW_WIDTH - 2 * m, config.WINDOW_HEIGHT - y - 48)
        inner = hud.draw_panel(surface, panel)
        row_h = fonts.grid.get_linesize() + 6
        for i, level in enumerate(self.world.levels):
            ry = inner.y + i * row_h
            if ry + row_h > inner.bottom:
                break
            selected = i == self.level_index
            if selected:
                pygame.draw.rect(
                    surface,
                    config.PANEL,
                    (inner.x - 6, ry - 2, inner.w + 12, row_h),
                    border_radius=4,
                )
            color = config.FOREGROUND if selected else config.MUTED
            label = fonts.grid.render(f"{level.id:<5} {level.title}", True, color)
            surface.blit(label, (inner.x + 8, ry))
            stars = self.app.progress.get(level.id, 0)
            hud.draw_stars(surface, fonts.grid, stars, inner.right - 70, ry)
            teaches = "  ".join(level.teaches)
            tl = fonts.small.render(
                teaches, True, config.PANEL_EDGE if not selected else config.ACCENT
            )
            surface.blit(tl, (inner.right - 90 - tl.get_width(), ry + 3))

        footer = fonts.small.render(
            "j/k level    h/l world    Enter play    q quit", True, config.MUTED
        )
        surface.blit(footer, (m, config.WINDOW_HEIGHT - 36))
