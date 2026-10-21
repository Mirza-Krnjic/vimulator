"""Core game loop and the scene stack."""

from __future__ import annotations

import pygame

from vimulator import config
from vimulator.levels import Level, all_levels, load_worlds
from vimulator.scenes import Fonts, Scene
from vimulator.scenes.level_select import LevelSelectScene
from vimulator.ui.text_grid import TextGrid
from vimulator.vim.keys import BACKSPACE, ENTER, ESC, Key


def key_from_event(event: pygame.event.Event) -> Key | None:
    """Map a KEYDOWN event to a Key, or None for keys the game ignores (modifiers, arrows)."""
    if event.key == pygame.K_ESCAPE:
        return ESC
    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
        return ENTER
    if event.key == pygame.K_BACKSPACE:
        return BACKSPACE
    if event.mod & pygame.KMOD_CTRL:
        name = pygame.key.name(event.key)
        return Key(char=name, ctrl=True) if len(name) == 1 else None
    text = getattr(event, "unicode", "")
    if text and text.isprintable():
        return Key(char=text)
    return None


class Game:
    """Owns the window and runs the events / update / draw loop over a scene stack."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        pygame.display.set_caption(config.TITLE)
        self.clock = pygame.time.Clock()
        pygame.key.set_repeat(400, 40)
        self.fonts = Fonts(
            grid=pygame.font.SysFont("monospace", config.GRID_FONT_SIZE),
            hud=pygame.font.SysFont("monospace", config.HUD_FONT_SIZE, bold=True),
            small=pygame.font.SysFont("monospace", config.SMALL_FONT_SIZE),
            title=pygame.font.SysFont("monospace", config.TITLE_FONT_SIZE, bold=True),
        )
        self.grid = TextGrid(self.fonts.grid)
        self.worlds = load_worlds()
        self.levels = all_levels(self.worlds)
        self.progress: dict[str, int] = {}
        self.scenes: list[Scene] = [LevelSelectScene(self)]
        self.running = False

    # --- scene stack -------------------------------------------------------------

    def push(self, scene: Scene) -> None:
        self.scenes.append(scene)

    def pop(self) -> None:
        if len(self.scenes) > 1:
            self.scenes.pop()

    def set_scenes(self, scenes: list[Scene]) -> None:
        self.scenes = list(scenes)

    def quit(self) -> None:
        self.running = False

    def next_level(self, level: Level) -> Level | None:
        ids = [lv.id for lv in self.levels]
        i = ids.index(level.id)
        return self.levels[i + 1] if i + 1 < len(self.levels) else None

    def pop_to_select(self, level: Level) -> None:
        world_index = next(i for i, w in enumerate(self.worlds) if w.number == level.world)
        level_index = next(
            i for i, lv in enumerate(self.worlds[world_index].levels) if lv.id == level.id
        )
        self.scenes = [LevelSelectScene(self, world_index, level_index)]

    # --- loop ------------------------------------------------------------------------

    def run(self) -> None:
        self.running = True
        try:
            while self.running:
                dt = self.clock.tick(config.FPS) / 1000.0
                self.handle_events()
                self.update(dt)
                self.draw()
        finally:
            pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                key = key_from_event(event)
                if key is not None and self.scenes:
                    self.scenes[-1].handle_key(key)

    def update(self, dt: float) -> None:
        if self.scenes:
            self.scenes[-1].update(dt)

    def draw(self) -> None:
        self.screen.fill(config.BACKGROUND)
        if self.scenes:
            self.scenes[-1].draw(self.screen)
        pygame.display.flip()
