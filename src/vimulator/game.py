"""Core game loop."""

import pygame

from vimulator import config


class Game:
    """Owns the window and runs the events / update / draw loop."""

    def __init__(self) -> None:
        pygame.init()
        self.screen = pygame.display.set_mode((config.WINDOW_WIDTH, config.WINDOW_HEIGHT))
        pygame.display.set_caption(config.TITLE)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 32)
        self.running = False

    def run(self) -> None:
        self.running = True
        try:
            while self.running:
                dt = self.clock.tick(config.FPS) / 1000.0
                self.handle_events()
                self.update(dt)
                self.draw()
        finally:
            pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False

    def update(self, dt: float) -> None:
        """Advance game state by `dt` seconds. Nothing to update yet."""

    def draw(self) -> None:
        self.screen.fill(config.BACKGROUND)
        text = self.font.render(config.TITLE, True, config.FOREGROUND)
        rect = text.get_rect(center=self.screen.get_rect().center)
        self.screen.blit(text, rect)
        pygame.display.flip()
