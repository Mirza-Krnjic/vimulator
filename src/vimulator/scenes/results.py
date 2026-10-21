"""After a level: stars, your keys against par, next / retry / back."""

from __future__ import annotations

import pygame

from vimulator import config
from vimulator.levels import Level
from vimulator.scenes import Scene
from vimulator.scoring import stars_for
from vimulator.ui import hud
from vimulator.vim.editor import Editor
from vimulator.vim.keys import Key, format_keys


class ResultsScene(Scene):
    def __init__(self, app, level: Level, editor: Editor) -> None:
        super().__init__(app)
        self.level = level
        self.keystrokes = editor.keystrokes
        self.your_keys = format_keys(editor.keys)
        self.stars = stars_for(self.keystrokes, level.par)
        app.progress[level.id] = max(app.progress.get(level.id, 0), self.stars)

    def handle_key(self, key: Key) -> None:
        from vimulator.scenes.play import PlayScene

        if key.name == "enter":
            nxt = self.app.next_level(self.level)
            if nxt is None:
                self.app.pop_to_select(self.level)
            else:
                self.app.set_scenes([self.app.scenes[0], PlayScene(self.app, nxt)])
            return
        if key.char == "r":
            self.app.set_scenes([self.app.scenes[0], PlayScene(self.app, self.level)])
        elif key.char == "q":
            self.app.pop_to_select(self.level)

    def draw(self, surface: pygame.Surface) -> None:
        self.app.scenes[-2].draw(surface) if len(self.app.scenes) > 1 else None
        shade = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 160))
        surface.blit(shade, (0, 0))

        fonts = self.app.fonts
        box = pygame.Rect(0, 0, 640, 330)
        box.center = (config.WINDOW_WIDTH // 2, config.WINDOW_HEIGHT // 2)
        inner = hud.draw_panel(surface, box)
        x, y = inner.x + 8, inner.y + 6

        title = fonts.hud.render(
            f"{self.level.id}  {self.level.title}  complete", True, config.FOREGROUND
        )
        surface.blit(title, (x, y))
        y += title.get_height() + 10
        hud.draw_stars(surface, fonts.title, self.stars, x, y - 10)
        y += fonts.title.get_linesize() - 4

        par = self.level.par
        verdict = "at par" if self.keystrokes <= par else f"{self.keystrokes - par} over par"
        line = fonts.hud.render(
            f"{self.keystrokes} keys, par {par}: {verdict}",
            True,
            config.GREEN if self.keystrokes <= par else config.PEACH,
        )
        surface.blit(line, (x, y))
        y += line.get_height() + 16

        for label, keys, color in (
            ("you", self.your_keys, config.FOREGROUND),
            ("par", self.level.par_keys, config.YELLOW),
        ):
            tag = fonts.small.render(f"{label}:", True, config.MUTED)
            surface.blit(tag, (x, y + 4))
            shown = keys if len(keys) <= 48 else keys[:45] + "..."
            seq = fonts.grid.render(shown, True, color)
            surface.blit(seq, (x + 50, y))
            y += seq.get_height() + 8

        footer = fonts.small.render("Enter next    r retry    q levels", True, config.MUTED)
        surface.blit(footer, (x, inner.bottom - footer.get_height() - 4))
