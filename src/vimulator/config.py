"""Static game configuration: window, fonts, layout, colours, scoring."""

TITLE = "Vimulator"
WINDOW_WIDTH = 1024
WINDOW_HEIGHT = 640
FPS = 60

# Fonts (SysFont monospace for now; a bundled font comes with the first real UI pass)
GRID_FONT_SIZE = 22
HUD_FONT_SIZE = 30
SMALL_FONT_SIZE = 17
TITLE_FONT_SIZE = 44

# Layout
MARGIN = 24
HEADER_HEIGHT = 56
GRAMMAR_HEIGHT = 48
FOOTER_HEIGHT = 120

# Colours (RGB), a Catppuccin Mocha-like palette
BACKGROUND = (30, 30, 46)
SURFACE = (24, 24, 37)
PANEL = (49, 50, 68)
PANEL_EDGE = (69, 71, 90)
FOREGROUND = (205, 214, 244)
MUTED = (147, 153, 178)
ACCENT = (137, 180, 250)
GREEN = (166, 227, 161)
YELLOW = (249, 226, 175)
RED = (243, 139, 168)
PEACH = (250, 179, 135)
MAUVE = (203, 166, 247)

CURSOR_NORMAL = FOREGROUND
CURSOR_INSERT = GREEN
HIGHLIGHT = YELLOW
GOAL_CURSOR = MAUVE
MODE_COLORS = {"NORMAL": ACCENT, "INSERT": GREEN, "COMMAND": PEACH}

# Scoring
HIGHLIGHT_SECONDS = 0.14
TWO_STAR_FACTOR = 1.5
HINT_AFTER_FACTOR = 2  # show the hint once keystrokes exceed par * this
