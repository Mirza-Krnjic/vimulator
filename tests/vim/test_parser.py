import pytest

from vimulator.vim.keys import parse_keys
from vimulator.vim.parser import Command, Invalid, Parser, Pending


def descriptions(notation: str) -> list[str]:
    parser = Parser()
    out = []
    for key in parse_keys(notation):
        result = parser.feed(key)
        if isinstance(result, Invalid):
            out.append("<invalid>")
        else:
            out.append(result.description)
    return out


@pytest.mark.parametrize(
    "keys, expected",
    [
        ("d2w", ["delete ...", "delete 2 ...", "delete 2 words"]),
        ("2dw", ["2 times ...", "delete 2 ...", "delete 2 words"]),
        ("2d3w", ["2 times ...", "delete 2 ...", "delete 6 ...", "delete 6 words"]),
        ("dd", ["delete ...", "delete 1 line"]),
        ("3dd", ["3 times ...", "delete 3 ...", "delete 3 lines"]),
        ("cw", ["change ...", "change 1 word"]),
        ("c$", ["change ...", "change to end of line"]),
        ("yy", ["yank ...", "yank 1 line"]),
        ("w", ["forward 1 word"]),
        ("3w", ["3 times ...", "forward 3 words"]),
        ("5j", ["5 times ...", "move down 5 lines"]),
        ("dj", ["delete ...", "delete 2 lines downward"]),
        ("x", ["delete 1 character"]),
        ("3x", ["3 times ...", "delete 3 characters"]),
        ("rz", ["replace with ...", "replace 1 character with 'z'"]),
        ("0", ["to start of line"]),
        ("10l", ["1 times ...", "10 times ...", "move right 10 characters"]),
        ("i", ["insert before cursor"]),
        ("A", ["append at end of line"]),
        ("<C-r>", ["redo"]),
        ("u", ["undo"]),
        (":", ["command line"]),
        ("z", ["<invalid>"]),
        ("dz", ["delete ...", "<invalid>"]),
        ("d<Esc>", ["delete ...", "<invalid>"]),
    ],
)
def test_descriptions(keys: str, expected: list[str]) -> None:
    assert descriptions(keys) == expected


def test_result_types() -> None:
    parser = Parser()
    assert isinstance(parser.feed(parse_keys("d")[0]), Pending)
    result = parser.feed(parse_keys("w")[0])
    assert isinstance(result, Command)
    assert result.spec.kind == "operator_motion"
    assert result.spec.operator == "d"
    assert result.spec.key == "w"
    assert not parser.pending


def test_zero_is_digit_after_count() -> None:
    parser = Parser()
    parser.feed(parse_keys("1")[0])
    result = parser.feed(parse_keys("0")[0])
    assert isinstance(result, Pending)
    assert parser.count1 == 10
