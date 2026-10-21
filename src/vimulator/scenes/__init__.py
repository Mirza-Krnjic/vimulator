"""Scenes the Game delegates to. Each handles keys, updates, and draws itself."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pygame

from vimulator.vim.keys import Key

if TYPE_CHECKING:
    from vimulator.game import Game


@dataclass(frozen=True)
class Fonts:
    grid: pygame.font.Font
    hud: pygame.font.Font
    small: pygame.font.Font
    title: pygame.font.Font


class Scene:
    def __init__(self, app: Game) -> None:
        self.app = app

    def handle_key(self, key: Key) -> None:  # noqa: B027 (intentionally empty default)
        pass

    def update(self, dt: float) -> None:  # noqa: B027
        pass

    def draw(self, surface: pygame.Surface) -> None:  # noqa: B027
        pass
