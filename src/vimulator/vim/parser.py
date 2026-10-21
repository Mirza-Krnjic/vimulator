"""Normal-mode key parser.

Feeds one key at a time and reports whether the command is still pending, complete, or
invalid. It also produces the plain-language description the grammar HUD shows live, so
`d`, `2`, `w` reads as "delete ...", "delete 2 ...", "delete 2 words".
"""

from __future__ import annotations

from dataclasses import dataclass

from vimulator.vim.keys import Key
from vimulator.vim.motions import MOTION_KEYS

OPERATORS = frozenset("dcy")
SIMPLE_KEYS = frozenset("xXpPuiaAIoOsSCD:")

_VERBS = {"d": "delete", "c": "change", "y": "yank"}


def _n(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def motion_move_desc(key: str, count: int) -> str:
    match key:
        case "h":
            return "move left " + _n(count, "character", "characters")
        case "l":
            return "move right " + _n(count, "character", "characters")
        case "j":
            return "move down " + _n(count, "line", "lines")
        case "k":
            return "move up " + _n(count, "line", "lines")
        case "w":
            return "forward " + _n(count, "word", "words")
        case "b":
            return "back " + _n(count, "word", "words")
        case "e":
            return "to end of word" if count == 1 else f"to end of {count} words"
        case "0":
            return "to start of line"
        case "^":
            return "to first non-blank"
        case "$":
            return "to end of line" if count == 1 else f"to end of line, {count - 1} down"
    return key


def motion_object_desc(key: str, count: int) -> str:
    match key:
        case "h":
            return _n(count, "character", "characters") + " left"
        case "l":
            return _n(count, "character", "characters")
        case "j":
            return f"{count + 1} lines downward"
        case "k":
            return f"{count + 1} lines upward"
        case "w":
            return _n(count, "word", "words")
        case "b":
            return _n(count, "word", "words") + " back"
        case "e":
            return "to end of word" if count == 1 else f"to end of {count} words"
        case "0":
            return "to start of line"
        case "^":
            return "to first non-blank"
        case "$":
            return "to end of line" if count == 1 else f"to end of line, {count - 1} down"
    return key


def simple_desc(key: str, count: int) -> str:
    match key:
        case "x":
            return "delete " + _n(count, "character", "characters")
        case "X":
            return "delete " + _n(count, "character", "characters") + " before cursor"
        case "p":
            return "put after cursor" + (f" {count} times" if count > 1 else "")
        case "P":
            return "put before cursor" + (f" {count} times" if count > 1 else "")
        case "u":
            return "undo"
        case "i":
            return "insert before cursor"
        case "a":
            return "append after cursor"
        case "A":
            return "append at end of line"
        case "I":
            return "insert at first non-blank"
        case "o":
            return "open line below"
        case "O":
            return "open line above"
        case "s":
            return "substitute " + _n(count, "character", "characters")
        case "S":
            return "substitute " + _n(count, "line", "lines")
        case "C":
            return "change to end of line"
        case "D":
            return "delete to end of line"
        case ":":
            return "command line"
    return key


@dataclass(frozen=True, slots=True)
class CommandSpec:
    kind: str  # motion | operator_motion | operator_line | simple | replace | redo
    key: str
    count: int = 1
    operator: str | None = None
    char: str | None = None


@dataclass(frozen=True, slots=True)
class Pending:
    description: str


@dataclass(frozen=True, slots=True)
class Command:
    description: str
    spec: CommandSpec


@dataclass(frozen=True, slots=True)
class Invalid:
    reason: str = ""


ParseResult = Pending | Command | Invalid


class Parser:
    """State machine over `[count] [operator [count]] motion`."""

    def __init__(self) -> None:
        self.count1: int | None = None
        self.operator: str | None = None
        self.count2: int | None = None
        self.want_char = False

    def reset(self) -> None:
        self.count1 = None
        self.operator = None
        self.count2 = None
        self.want_char = False

    @property
    def pending(self) -> bool:
        return (
            self.count1 is not None
            or self.operator is not None
            or self.count2 is not None
            or self.want_char
        )

    @property
    def count(self) -> int:
        return (self.count1 or 1) * (self.count2 or 1)

    def _pending_desc(self) -> str:
        if self.want_char:
            return "replace with ..."
        if self.operator is not None:
            verb = _VERBS[self.operator]
            if self.count2 is not None:
                return f"{verb} {self.count} ..."
            if self.count1 is not None:
                return f"{verb} {self.count1} ..."
            return f"{verb} ..."
        if self.count1 is not None:
            return f"{self.count1} times ..."
        return ""

    def feed(self, key: Key) -> ParseResult:
        if self.want_char:
            count = self.count
            self.reset()
            if not key.is_printable:
                return Invalid()
            assert key.char is not None
            desc = "replace " + _n(count, "character", "characters") + f" with '{key.char}'"
            return Command(desc, CommandSpec("replace", "r", count, char=key.char))

        if key.name == "esc":
            self.reset()
            return Invalid()

        if key.ctrl:
            pending = self.pending
            self.reset()
            if key.char == "r" and not pending:
                return Command("redo", CommandSpec("redo", "<C-r>"))
            return Invalid("unknown key")

        if not key.is_printable:
            self.reset()
            return Invalid("unknown key")

        assert key.char is not None
        c = key.char

        if c.isdigit() and not (c == "0" and self._count_slot() is None):
            self._add_digit(int(c))
            return Pending(self._pending_desc())

        if self.operator is None:
            count = self.count
            if c in OPERATORS:
                self.operator = c
                return Pending(self._pending_desc())
            if c == "r":
                self.want_char = True
                return Pending(self._pending_desc())
            self.reset()
            if c in MOTION_KEYS:
                return Command(motion_move_desc(c, count), CommandSpec("motion", c, count))
            if c in SIMPLE_KEYS:
                return Command(simple_desc(c, count), CommandSpec("simple", c, count))
            return Invalid("unknown key")

        op = self.operator
        count = self.count
        self.reset()
        verb = _VERBS[op]
        if c == op:
            desc = f"{verb} " + _n(count, "line", "lines")
            return Command(desc, CommandSpec("operator_line", c, count, operator=op))
        if c in MOTION_KEYS:
            desc = f"{verb} {motion_object_desc(c, count)}"
            return Command(desc, CommandSpec("operator_motion", c, count, operator=op))
        return Invalid("unknown key")

    def _count_slot(self) -> int | None:
        return self.count2 if self.operator is not None else self.count1

    def _add_digit(self, d: int) -> None:
        if self.operator is not None:
            self.count2 = (self.count2 or 0) * 10 + d
        else:
            self.count1 = (self.count1 or 0) * 10 + d
