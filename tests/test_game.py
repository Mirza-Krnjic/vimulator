"""Drive the real Game through synthetic KEYDOWN events under the dummy video driver."""

import pygame
import pytest

from vimulator.game import Game, key_from_event
from vimulator.scenes.level_select import LevelSelectScene
from vimulator.scenes.play import PlayScene
from vimulator.scenes.results import ResultsScene
from vimulator.vim.keys import Key, parse_keys


def event_for(key: Key) -> pygame.event.Event:
    if key.name == "esc":
        return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="\x1b")
    if key.name == "enter":
        return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0, unicode="\r")
    if key.name == "backspace":
        return pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, mod=0, unicode="\x08")
    assert key.char is not None
    if key.ctrl:
        return pygame.event.Event(
            pygame.KEYDOWN, key=pygame.key.key_code(key.char), mod=pygame.KMOD_CTRL, unicode=""
        )
    code = pygame.key.key_code(key.char) if key.char.isalpha() else pygame.K_UNKNOWN
    return pygame.event.Event(pygame.KEYDOWN, key=code, mod=0, unicode=key.char)


@pytest.fixture
def game():
    g = Game()
    yield g
    pygame.quit()


def send(game: Game, notation: str) -> None:
    for key in parse_keys(notation):
        pygame.event.post(event_for(key))
        game.handle_events()
        game.update(0.016)
        game.draw()


def test_key_mapping_round_trips() -> None:
    pygame.init()
    for notation in ("a", "$", "<Esc>", "<CR>", "<BS>", "<C-r>", "<Space>"):
        key = parse_keys(notation)[0]
        assert key_from_event(event_for(key)) == key, notation
    shift_only = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_LSHIFT, mod=0, unicode="")
    assert key_from_event(shift_only) is None


def test_play_first_two_levels_at_par(game: Game) -> None:
    assert isinstance(game.scenes[-1], LevelSelectScene)
    send(game, "<CR>")
    play = game.scenes[-1]
    assert isinstance(play, PlayScene) and play.level.id == "1-1"
    send(game, play.level.par_keys)
    results = game.scenes[-1]
    assert isinstance(results, ResultsScene)
    assert results.stars == 3
    assert game.progress["1-1"] == 3

    send(game, "<CR>")
    play = game.scenes[-1]
    assert isinstance(play, PlayScene) and play.level.id == "1-2"
    send(game, "ihi<Esc>")
    assert isinstance(game.scenes[-1], ResultsScene)
    assert game.scenes[-1].stars == 3


def test_over_par_gives_fewer_stars_and_retry_works(game: Game) -> None:
    send(game, "j<CR>")  # 1-2 "Say hi", par 4 (ihi<Esc>)
    send(game, "ih<Esc>xihi<Esc>")  # a false start, then the real thing: 8 keys
    results = game.scenes[-1]
    assert isinstance(results, ResultsScene)
    assert results.keystrokes == 8
    assert results.stars == 1
    send(game, "r")
    play = game.scenes[-1]
    assert isinstance(play, PlayScene) and play.level.id == "1-2"
    assert play.editor.keystrokes == 0
    send(game, "ih<Esc>ai<Esc>")  # 6 keys: within par * 1.5
    results = game.scenes[-1]
    assert isinstance(results, ResultsScene)
    assert results.stars == 2


def test_grammar_hud_and_flash(game: Game) -> None:
    send(game, "llll<CR>")  # world 5, level 5-1 (dw)
    play = game.scenes[-1]
    assert isinstance(play, PlayScene) and play.level.id == "5-1"
    send(game, "d")
    assert play.description == "delete ..." and play.pending
    send(game, "2")
    assert play.description == "delete 2 ..."
    send(game, "w")
    assert play.description == "delete 2 words" and not play.pending
    assert play.flash_lines == ["delete this word"]
    assert play.flash_cells
    play.update(1.0)
    assert play.flash_lines is None


def test_q_bang_restarts_level(game: Game) -> None:
    send(game, "jjjj<CR>")  # 1-5 "Save and quit", starts in Normal mode
    send(game, "jj:q!<CR>")
    play = game.scenes[-1]
    assert isinstance(play, PlayScene)
    assert play.editor.keystrokes == 0


def test_quit_from_level_select(game: Game) -> None:
    game.running = True
    send(game, "q")
    assert game.running is False
