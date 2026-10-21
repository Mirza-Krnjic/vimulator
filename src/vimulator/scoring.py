"""Par-based scoring."""

import math

from vimulator import config


def stars_for(keystrokes: int, par: int) -> int:
    if keystrokes <= par:
        return 3
    if keystrokes <= math.ceil(par * config.TWO_STAR_FACTOR):
        return 2
    return 1
