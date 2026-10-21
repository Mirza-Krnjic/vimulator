"""Keys as the engine sees them, plus Vim-notation parsing for level files and tests."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Key:
    """One keystroke.

    Exactly one of `char` (a printable character) or `name` (`esc`, `enter`, `backspace`) is set.
    `ctrl` marks a Ctrl chord on `char`.
    """

    char: str | None = None
    name: str | None = None
    ctrl: bool = False

    def __post_init__(self) -> None:
        if (self.char is None) == (self.name is None):
            raise ValueError("Key needs exactly one of char or name")
        if self.char is not None and len(self.char) != 1:
            raise ValueError("Key.char must be a single character")

    @property
    def is_printable(self) -> bool:
        return self.char is not None and not self.ctrl

    def notation(self) -> str:
        if self.name == "esc":
            return "<Esc>"
        if self.name == "enter":
            return "<CR>"
        if self.name == "backspace":
            return "<BS>"
        assert self.char is not None
        if self.ctrl:
            return f"<C-{self.char}>"
        if self.char == "<":
            return "<lt>"
        if self.char == " ":
            return "<Space>"
        return self.char


ESC = Key(name="esc")
ENTER = Key(name="enter")
BACKSPACE = Key(name="backspace")


def key(char: str) -> Key:
    return Key(char=char)


def ctrl(char: str) -> Key:
    return Key(char=char.lower(), ctrl=True)


_SPECIAL = {
    "esc": ESC,
    "cr": ENTER,
    "enter": ENTER,
    "return": ENTER,
    "bs": BACKSPACE,
    "lt": Key(char="<"),
    "space": Key(char=" "),
}
_CTRL = re.compile(r"c-(.)", re.IGNORECASE)


def parse_keys(notation: str) -> list[Key]:
    """Turn Vim notation (`dw`, `ifoo<Esc>`, `<C-r>`) into keys."""
    keys: list[Key] = []
    i = 0
    while i < len(notation):
        ch = notation[i]
        if ch == "<":
            close = notation.find(">", i + 1)
            if close == -1:
                raise ValueError(f"unterminated <...> in {notation!r}")
            inner = notation[i + 1 : close]
            special = _SPECIAL.get(inner.lower())
            if special is not None:
                keys.append(special)
            else:
                m = _CTRL.fullmatch(inner)
                if m is None:
                    raise ValueError(f"unknown key name <{inner}> in {notation!r}")
                keys.append(ctrl(m.group(1)))
            i = close + 1
        else:
            keys.append(Key(char=ch))
            i += 1
    return keys


def format_keys(keys: list[Key]) -> str:
    return "".join(k.notation() for k in keys)
