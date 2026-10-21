import pytest

from vimulator.vim.keys import BACKSPACE, ENTER, ESC, Key, ctrl, format_keys, parse_keys


def test_parse_literal_and_special() -> None:
    keys = parse_keys("ab<Esc><CR><BS><C-r><lt><Space>")
    assert keys == [
        Key(char="a"),
        Key(char="b"),
        ESC,
        ENTER,
        BACKSPACE,
        ctrl("r"),
        Key(char="<"),
        Key(char=" "),
    ]


def test_round_trip() -> None:
    notation = "ifoo<Esc>3x<C-r><lt><Space>$"
    assert format_keys(parse_keys(notation)) == notation


def test_unknown_name_raises() -> None:
    with pytest.raises(ValueError):
        parse_keys("<Nope>")


def test_key_validation() -> None:
    with pytest.raises(ValueError):
        Key()
    with pytest.raises(ValueError):
        Key(char="ab")
