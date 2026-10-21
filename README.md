# Vimulator

A game for learning Vim, built in Python with [pygame-ce](https://pyga.me/).

Each level shows a buffer and a goal. You edit with real Vim keys until the buffer matches the
goal. Every keystroke counts; meeting par earns three stars. A strip above the buffer reads
your command back to you as you type it, so `d`, `2`, `w` becomes "delete 2 words".

## Requirements

- Python 3.12+ (3.14 pinned in `.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Run

```sh
uv sync
uv run vimulator
```

Level select: `j`/`k` pick a level, `h`/`l` switch world, Enter plays, `q` quits.
In a level: the keys taught so far. `:q` goes back to the list, `:e!` restarts the level, `:wq` submits where the level asks for it.
After a level: Enter for the next one, `r` to retry, `q` back to the list.

## Develop

```sh
uv run pytest -q       # tests, headless; the Neovim oracle runs when nvim is on PATH
uv run ruff check .    # lint
uv run ruff format .   # format
```

## Layout

```
src/vimulator/
  main.py        entry point
  game.py        main loop, scene stack, key mapping
  config.py      window size, fonts, colours, scoring
  vim/           the editor model: buffer, cursor, motions, operators, parser (no pygame)
  levels/        level data classes and the JSON worlds in levels/data/
  scenes/        level select, play, results
  ui/            text grid with glyph cache, HUD pieces
tests/           pytest suite; tests/vim/cases.py is the table both the engine and Neovim run
```
