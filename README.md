# Vimulator

A game for learning Vim, built in Python with [pygame-ce](https://pyga.me/).

## Requirements

- Python 3.12+ (3.14 pinned in `.python-version`)
- [uv](https://docs.astral.sh/uv/)

## Run

```sh
uv sync
uv run vimulator
```

Press `Esc` or close the window to quit.

## Develop

```sh
uv run pytest        # tests
uv run ruff check .  # lint
uv run ruff format . # format
```

## Layout

```
src/vimulator/
  main.py    entry point
  game.py    main loop (events / update / draw)
  config.py  window size, FPS, colors
tests/       pytest suite (runs headless)
```
