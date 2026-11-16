"""
Main Menu — Title screen with animated bunny, play/continue, settings.
"""
import pygame
import math
from core.state_machine import GameState
from systems.sound_manager import get_sound_manager
from systems.save_system import list_saves, load_game
from utils.asset_loader import render_text
from utils.draw_helpers import draw_bunny_icon, draw_rounded_panel
import settings as S


class MainMenuState(GameState):
    def __init__(self, game):
        super().__init__(game)
        self._sm = get_sound_manager()
        self.time = 0.0
        self._particles: list[dict] = []
        self._has_save = False

        # Buttons — built in enter() once we know save state
        self._buttons: list[dict] = []

    def enter(self, **params):
        self.time = 0.0
        self._error = ""
        self._check_saves()
        self._build_buttons()

    def _check_saves(self):
        saves = list_saves()
        self._has_save = len(saves) > 0

    def _build_buttons(self):
        self._buttons.clear()
        cx = 232
        by = 400
        bw, bh = 320, 48
        gap = 62

        if self._has_save:
            self._buttons.append({
                "rect": pygame.Rect(cx - bw // 2, by, bw, bh),
                "text": "Continue", "color": S.COLOR_ACCENT2,
                "action": self._continue_game, "hover": False,
            })
            by += gap
            self._buttons.append({
                "rect": pygame.Rect(cx - bw // 2, by, bw, bh),
                "text": "New Game", "color": S.COLOR_BUTTON,
                "action": self._new_game, "hover": False,
            })
        else:
            self._buttons.append({
                "rect": pygame.Rect(cx - bw // 2, by, bw, bh),
                "text": "Play", "color": S.COLOR_BUTTON,
                "action": self._new_game, "hover": False,
            })
        by += gap
        self._buttons.append({
            "rect": pygame.Rect(cx - bw // 2, by, bw, bh),
            "text": "Settings", "color": (100, 100, 140),
            "action": self._open_settings, "hover": False,
        })
        by += gap
        self._buttons.append({
            "rect": pygame.Rect(cx - bw // 2, by, bw, bh),
            "text": "How to Play", "color": (80, 160, 120),
            "action": self._open_help, "hover": False,
        })

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            for btn in self._buttons:
                btn["hover"] = btn["rect"].collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._buttons:
                if btn["rect"].collidepoint(event.pos):
                    self._sm.play("click")
                    btn["action"]()
                    return

    def update(self, dt: float):
        self.time += dt

    def draw(self, surface: pygame.Surface):
        from ui.kingdom import landscape, label, tree
        from utils.draw_helpers import draw_building_shape
        surface.fill(S.COLOR_BG)
        if not hasattr(self, "_landscape"):
            self._landscape = landscape(820, 800)
        surface.blit(self._landscape, (580, 0))
        pygame.draw.circle(surface, (224, 203, 143), (1150, 130), 54)
        # A winding path, village, and its little ruler.
        pygame.draw.lines(surface, (153, 148, 101), False,
                          [(910,800),(1000,640),(870,520),(1010,390)], 42)
        for bid, rect in [("castle", (880,275,200,200)), ("carrot_farm", (700,490,110,110)),
                          ("lumber_burrow", (1110,450,110,110)), ("academy", (1100,620,100,100))]:
            draw_building_shape(surface, pygame.Rect(rect), S.BUILDING_COLORS[bid], bid)
        draw_bunny_icon(surface, pygame.Rect(900,560+int(math.sin(self.time*2)*6),90,90), (247,237,211))
        label(surface, "A KINGDOM OF FLUFF & STRATEGY", (72,110), 14, S.COLOR_ACCENT, True)
        label(surface, "Bunny", (68,153), 84, S.COLOR_TEXT, True)
        label(surface, "Lords", (68,236), 84, S.COLOR_ACCENT, True)
        label(surface, "Build a burrow. Raise a brigade.", (72,342), 21)
        label(surface, "Make a little history.", (72,371), 18, S.COLOR_TEXT_DIM)
        for btn in self._buttons:
            color = tuple(min(255,c+18) for c in btn["color"]) if btn["hover"] else btn["color"]
            draw_rounded_panel(surface, btn["rect"], color, radius=9, alpha=240)
            text = render_text(btn["text"], 20, S.COLOR_WHITE, bold=True)
            surface.blit(text, text.get_rect(center=btn["rect"].center))
        label(surface, getattr(self, "_error", ""), (72,710), 13, S.COLOR_DANGER)
        label(surface, "WOODLAND UPDATE  /  v2.0", (72,755), 12, S.COLOR_TEXT_DIM, True)
        label(surface, "F11  Fullscreen", (1200,765), 12, (220,231,208))

    def _new_game(self):
        """Start a fresh game by resetting all progress."""
        # Archive existing slots before a new autosave can replace them.
        import shutil
        import time
        from pathlib import Path
        saves = list_saves()
        if saves:
            archive = Path(saves[0]["path"]).parent / "archive" / str(time.time_ns())
            try:
                archive.mkdir(parents=True, exist_ok=True)
                for saved in saves:
                    shutil.copy2(saved["path"], archive / saved["filename"])
            except OSError:
                self._error = "Could not archive your previous kingdom. Check saves folder permissions."
                return
        # Access base_view state and reset it
        base_state = self.game.state_manager._registry.get("base_view")
        if base_state:
            base_state.reset_to_new_game()  # type: ignore[attr-defined]
        self.game.state_manager.transition_to("base_view")

    def _continue_game(self):
        """Load the most recent save and start."""
        saves = list_saves()
        base = self.game.state_manager._registry.get("base_view")
        for saved in saves:
            if base and load_game(base, saved["path"]):
                self.game.state_manager.transition_to("base_view")
                return
        self._error = "This save could not be loaded. Your existing files have been preserved."

    def _open_settings(self):
        self._sm.play("click")
        self.game.state_manager.push("settings")

    def _open_help(self):
        self._sm.play("click")
        self.game.state_manager.push("help_screen")
