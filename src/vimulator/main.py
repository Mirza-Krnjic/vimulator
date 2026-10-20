"""Application entry point."""

from vimulator.game import Game


def main() -> int:
    Game().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
