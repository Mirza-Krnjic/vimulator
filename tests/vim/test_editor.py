import pytest

from vimulator.vim.editor import Editor
from vimulator.vim.keys import parse_keys
from vimulator.vim.modes import Mode

from .cases import CASES


@pytest.mark.parametrize("case", CASES, ids=[c[0] for c in CASES])
def test_editor_matches_vim(case) -> None:
    name, start, cursor, keys, expected_lines, expected_cursor = case
    editor = Editor(start, cursor)
    editor.feed_all(parse_keys(keys))
    assert editor.lines == expected_lines, name
    assert editor.cursor.pos == expected_cursor, name
    assert editor.mode is Mode.NORMAL


def test_keystrokes_count_every_key() -> None:
    editor = Editor(["abc"])
    editor.feed_all(parse_keys("ifoo<Esc>3x<C-r>"))
    assert editor.keystrokes == 8


def test_start_in_insert_mode() -> None:
    editor = Editor(["ab"], (0, 1))
    editor.enter_insert()
    editor.feed_all(parse_keys("x<Esc>"))
    assert editor.lines == ["axb"]
    assert editor.mode is Mode.NORMAL
    editor.feed_all(parse_keys("u"))
    assert editor.lines == ["ab"]


def test_cmdline_wq_submits() -> None:
    editor = Editor(["x"])
    results = [editor.feed(k) for k in parse_keys(":wq<CR>")]
    assert editor.mode is Mode.NORMAL
    assert results[-1].submitted
    assert editor.cmdline == ""


def test_cmdline_q_quits_and_e_bang_restarts() -> None:
    for notation in (":q<CR>", ":q!<CR>", ":qa<CR>"):
        editor = Editor(["x"])
        result = editor.feed_all(parse_keys(notation))
        assert result.quit and not result.restart, notation
    for notation in (":e<CR>", ":e!<CR>"):
        editor = Editor(["x"])
        result = editor.feed_all(parse_keys(notation))
        assert result.restart and not result.quit, notation


def test_cmdline_esc_and_backspace_leave() -> None:
    editor = Editor(["x"])
    editor.feed_all(parse_keys(":w<Esc>"))
    assert editor.mode is Mode.NORMAL
    editor.feed_all(parse_keys(":<BS>"))
    assert editor.mode is Mode.NORMAL


def test_feed_result_highlight_for_operator() -> None:
    editor = Editor(["foo bar baz"], (0, 4))
    result = editor.feed_all(parse_keys("dw"))
    assert result.highlight is not None
    assert result.highlight.start == (0, 4)
    assert result.before == ["foo bar baz"]
    assert result.changed


def test_feed_result_pending_description() -> None:
    editor = Editor(["foo bar"])
    assert editor.feed_all(parse_keys("d")).description == "delete ..."
    assert editor.feed_all(parse_keys("2")).description == "delete 2 ..."
    result = editor.feed_all(parse_keys("w"))
    assert result.description == "delete 2 words"
    assert not result.pending
