"""HUD pieces: mode badge, grammar strip, keystroke counter, stars, panels."""

from __future__ import annotations

import pygame

from vimulator import config

Color = tuple[int, int, int]


def draw_panel(
    surface: pygame.Surface,
    rect: pygame.Rect,
    title: str | None = None,
    font: pygame.font.Font | None = None,
) -> pygame.Rect:
    """Draw a panel background and optional title. Returns the inner content rect."""
    pygame.draw.rect(surface, config.SURFACE, rect, border_radius=8)
    pygame.draw.rect(surface, config.PANEL_EDGE, rect, 1, border_radius=8)
    inner = rect.inflate(-2 * 14, -2 * 12)
    if title and font:
        label = font.render(title, True, config.MUTED)
        surface.blit(label, (inner.x, inner.y))
        inner = pygame.Rect(
            inner.x, inner.y + label.get_height() + 6, inner.w, inner.h - label.get_height() - 6
        )
    return inner


def draw_mode_badge(
    surface: pygame.Surface, font: pygame.font.Font, mode: str, right: int, y: int
) -> None:
    color = config.MODE_COLORS.get(mode, config.MUTED)
    label = font.render(f" {mode} ", True, config.BACKGROUND)
    rect = label.get_rect()
    rect.topright = (right, y)
    pygame.draw.rect(surface, color, rect.inflate(8, 4), border_radius=6)
    surface.blit(label, rect)


def draw_grammar(
    surface: pygame.Surface, font: pygame.font.Font, text: str, x: int, y: int, pending: bool
) -> None:
    color = config.MUTED if pending or not text else config.YELLOW
    label = font.render(text if text else "...", True, color)
    surface.blit(label, (x, y))


def draw_counter(
    surface: pygame.Surface, font: pygame.font.Font, keystrokes: int, par: int, right: int, y: int
) -> None:
    color = config.GREEN if keystrokes <= par else config.PEACH
    label = font.render(f"keys {keystrokes}   par {par}", True, color)
    rect = label.get_rect()
    rect.topright = (right, y)
    surface.blit(label, rect)


def draw_stars(
    surface: pygame.Surface, font: pygame.font.Font, stars: int, x: int, y: int, total: int = 3
) -> int:
    """Draw filled and empty stars. Returns the x after the last one."""
    for i in range(total):
        color = config.YELLOW if i < stars else config.PANEL_EDGE
        label = font.render("*", True, color)
        surface.blit(label, (x, y))
        x += label.get_width() + 2
    return x


def draw_text_block(
    surface: pygame.Surface,
    font: pygame.font.Font,
    lines: list[str],
    x: int,
    y: int,
    color: Color,
    line_gap: int = 2,
) -> int:
    """Draw pre-wrapped lines top-down. Returns the y after the last line."""
    for line in lines:
        label = font.render(line, True, color)
        surface.blit(label, (x, y))
        y += label.get_height() + line_gap
    return y
