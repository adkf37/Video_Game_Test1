"""
Game — Main application class.  Owns the loop, state manager, and event bus.
"""
import pygame
import json
from pathlib import Path
from core.state_machine import StateManager
from core.event_bus import EventBus
from systems.sound_manager import get_sound_manager
import settings as S


class Game:
    def __init__(self):
        # Pygame init
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        if pygame.mixer.get_init():
            pygame.mixer.set_num_channels(16)

        self.fullscreen = False
        self._display_flags = pygame.RESIZABLE
        if pygame.display.get_driver() != "dummy":
            self._display_flags |= pygame.SCALED
        self.screen = pygame.display.set_mode((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), self._display_flags)
        pygame.display.set_caption(S.GAME_TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.show_fps = False

        # Core systems
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.sound_manager = get_sound_manager()
        self._load_preferences()

        # Register states (imported here to avoid circular deps)
        from states.main_menu import MainMenuState
        from states.base_view import BaseViewState
        from states.hero_management import HeroManagementState
        from states.battle_view import BattleViewState
        from states.world_map import WorldMapState
        from states.settings_state import SettingsState
        from states.pause_menu import PauseMenuState
        from states.help_screen import HelpScreenState
        from states.victory_animation import VictoryAnimationState

        self.state_manager.register("main_menu", MainMenuState(self))
        self.state_manager.register("base_view", BaseViewState(self))
        self.state_manager.register("hero_management", HeroManagementState(self))
        self.state_manager.register("battle_view", BattleViewState(self))
        self.state_manager.register("world_map", WorldMapState(self))
        self.state_manager.register("settings", SettingsState(self))
        self.state_manager.register("pause_menu", PauseMenuState(self))
        self.state_manager.register("help_screen", HelpScreenState(self))
        self.state_manager.register("victory_animation", VictoryAnimationState(self))

        # Start at main menu
        self.state_manager.push("main_menu")

    def run(self):
        while self.running:
            dt = self.clock.tick(S.FPS) / 1000.0
            dt = min(dt, 0.05)  # prevent spiral of death

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self.fullscreen = not self.fullscreen
                    flags = self._display_flags | (pygame.FULLSCREEN if self.fullscreen else 0)
                    self.screen = pygame.display.set_mode((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), flags)
                else:
                    self.state_manager.handle_event(event)

            self.state_manager.update(dt)
            self.state_manager.draw(self.screen)

            # FPS counter (top-right)
            if self.show_fps:
                fps_text = f"FPS: {int(self.clock.get_fps())}"
                font = pygame.font.SysFont("segoeui", 14)
                fps_surf = font.render(fps_text, True, S.COLOR_TEXT_DIM)
                self.screen.blit(fps_surf,
                                 (S.SCREEN_WIDTH - fps_surf.get_width() - 8, 4))

            pygame.display.flip()

        self.save_on_exit()
        self.save_preferences()
        pygame.quit()

    def save_on_exit(self):
        base = self.state_manager._registry["base_view"]
        if base in self.state_manager.stack and base.buildings:
            battle = self.state_manager._registry["battle_view"]
            if battle in self.state_manager.stack and battle._phase == "battle":
                battle._end_battle()
            base.save_progress()

    @property
    def preferences_path(self):
        return Path(__file__).resolve().parents[1] / "preferences.json"

    def _load_preferences(self):
        try:
            data = json.loads(self.preferences_path.read_text(encoding="utf-8"))
            self.sound_manager.set_master_volume(float(data.get("master_volume", .7)))
            self.sound_manager.set_sfx_volume(float(data.get("sfx_volume", .5)))
            self.sound_manager.enabled = bool(data.get("sound_enabled", True))
            self.show_fps = bool(data.get("show_fps", False))
        except (OSError, ValueError, TypeError, AttributeError):
            pass

    def save_preferences(self):
        data = {"master_volume": self.sound_manager.master_volume,
                "sfx_volume": self.sound_manager.sfx_volume,
                "sound_enabled": self.sound_manager.enabled, "show_fps": self.show_fps}
        try:
            path = self.preferences_path
            temporary = path.with_suffix(".tmp")
            temporary.write_text(json.dumps(data, indent=2), encoding="utf-8")
            temporary.replace(path)
        except OSError:
            pass
