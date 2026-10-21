"""Level and world data, loaded from the JSON files in `data/`."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib import resources

from vimulator.vim.editor import Editor
from vimulator.vim.keys import parse_keys

Pos = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Level:
    id: str
    world: int
    title: str
    brief: str
    start: tuple[str, ...]
    cursor: Pos
    start_mode: str  # "normal" or "insert"
    prelude_keys: str  # applied before play, not counted (lets a level open "after a mistake")
    goal: tuple[str, ...]
    goal_cursor: Pos | None
    requires_submit: bool
    par: int
    par_keys: str
    teaches: tuple[str, ...]
    hint: str


@dataclass(frozen=True, slots=True)
class World:
    number: int
    title: str
    intro: str
    levels: tuple[Level, ...]


def _level(world: int, raw: dict) -> Level:
    par_keys = raw["par_keys"]
    par = len(parse_keys(par_keys))
    if raw.get("par", par) != par:
        raise ValueError(f"level {raw['id']}: par {raw['par']} but par_keys has {par} keys")
    cursor = raw.get("cursor", [0, 0])
    goal_cursor = raw.get("goal_cursor")
    start_mode = raw.get("start_mode", "normal")
    if start_mode not in {"normal", "insert"}:
        raise ValueError(f"level {raw['id']}: bad start_mode {start_mode!r}")
    return Level(
        id=raw["id"],
        world=world,
        title=raw["title"],
        brief=raw["brief"],
        start=tuple(raw["start"]),
        cursor=(cursor[0], cursor[1]),
        start_mode=start_mode,
        prelude_keys=raw.get("prelude_keys", ""),
        goal=tuple(raw["goal"]),
        goal_cursor=None if goal_cursor is None else (goal_cursor[0], goal_cursor[1]),
        requires_submit=bool(raw.get("requires_submit", False)),
        par=par,
        par_keys=par_keys,
        teaches=tuple(raw.get("teaches", [])),
        hint=raw.get("hint", ""),
    )


def load_worlds() -> list[World]:
    data_dir = resources.files("vimulator.levels") / "data"
    worlds: list[World] = []
    seen: set[str] = set()
    for entry in sorted(data_dir.iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".json"):
            continue
        raw = json.loads(entry.read_text(encoding="utf-8"))
        number = int(raw["world"])
        levels = tuple(_level(number, lv) for lv in raw["levels"])
        for lv in levels:
            if lv.id in seen:
                raise ValueError(f"duplicate level id {lv.id}")
            seen.add(lv.id)
        worlds.append(World(number, raw["title"], raw.get("intro", ""), levels))
    return worlds


def all_levels(worlds: list[World]) -> list[Level]:
    return [lv for w in worlds for lv in w.levels]


def start_editor(level: Level) -> Editor:
    """An editor positioned at the level's starting state, with zero keystrokes counted."""
    editor = Editor(list(level.start), level.cursor, insert=level.start_mode == "insert")
    if level.prelude_keys:
        editor.feed_all(parse_keys(level.prelude_keys))
        editor.keys.clear()
    return editor
