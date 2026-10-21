from vimulator.levels import all_levels, load_worlds, start_editor
from vimulator.vim.keys import parse_keys
from vimulator.vim.modes import Mode


def test_worlds_load_in_order() -> None:
    worlds = load_worlds()
    assert [w.number for w in worlds] == [1, 2, 3, 4, 5]
    assert all(w.levels for w in worlds)
    assert all(w.intro for w in worlds)


def test_every_par_solution_reaches_goal_in_par_keystrokes() -> None:
    for level in all_levels(load_worlds()):
        editor = start_editor(level)
        result = editor.feed_all(parse_keys(level.par_keys))
        assert editor.lines == list(level.goal), level.id
        assert editor.mode is Mode.NORMAL, level.id
        assert editor.keystrokes == level.par, level.id
        if level.goal_cursor is not None:
            assert editor.cursor.pos == level.goal_cursor, level.id
        if level.requires_submit:
            assert result.submitted, level.id


def test_levels_are_not_already_solved_at_start() -> None:
    for level in all_levels(load_worlds()):
        editor = start_editor(level)
        solved = (
            editor.lines == list(level.goal)
            and editor.mode is Mode.NORMAL
            and (level.goal_cursor is None or editor.cursor.pos == level.goal_cursor)
            and not level.requires_submit
        )
        assert not solved, f"{level.id} is solved before any key is pressed"
