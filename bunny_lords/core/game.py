"""
Game — Main application class.  Owns the loop, state manager, and event bus.
"""
import pygame
from core.state_machine import StateManager
from core.event_bus import EventBus
import settings as S


class Game:
    def __init__(self):
        # Pygame init
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        pygame.mixer.set_num_channels(16)

        self.screen = pygame.display.set_mode(
            (S.SCREEN_WIDTH, S.SCREEN_HEIGHT))
        pygame.display.set_caption(S.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        # Core systems
        self.event_bus = EventBus()
        self.state_manager = StateManager()

        # Register states (imported here to avoid circular deps)
        from states.main_menu import MainMenuState
        from states.base_view import BaseViewState
        from states.hero_management import HeroManagementState

        self.state_manager.register("main_menu", MainMenuState(self))
        self.state_manager.register("base_view", BaseViewState(self))
        self.state_manager.register("hero_management", HeroManagementState(self))

        # Start at main menu
        self.state_manager.push("main_menu")

    def run(self):
        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0
            dt = min(dt, 0.05)  # prevent spiral of death

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                else:
                    self.state_manager.handle_event(event)

            self.state_manager.update(dt)
            self.state_manager.draw(self.screen)

            # FPS counter (top-right)
            fps_text = f"FPS: {int(self.clock.get_fps())}"
            font = pygame.font.SysFont("segoeui", 14)
            fps_surf = font.render(fps_text, True, S.COLOR_TEXT_DIM)
            self.screen.blit(fps_surf,
                             (S.SCREEN_WIDTH - fps_surf.get_width() - 8, 4))

            pygame.display.flip()

        pygame.quit()
