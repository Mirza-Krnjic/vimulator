import pygame

import vimulator
from vimulator.game import Game


def test_version() -> None:
    assert vimulator.__version__ == "0.1.0"


def test_game_constructs_and_draws_headless() -> None:
    game = Game()
    try:
        game.handle_events()
        game.update(0.016)
        game.draw()
        assert game.screen.get_size() == (1024, 640)
    finally:
        pygame.quit()
