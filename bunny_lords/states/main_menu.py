"""
Main Menu — Title screen with animated bunny, play/continue, settings.
"""
import pygame
import math
from core.state_machine import GameState
from systems.sound_manager import get_sound_manager
from systems.save_system import list_saves, load_game, delete_save
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
        self._check_saves()
        self._build_buttons()

    def _check_saves(self):
        saves = list_saves()
        self._has_save = len(saves) > 0

    def _build_buttons(self):
        self._buttons.clear()
        cx = S.SCREEN_WIDTH // 2
        by = S.SCREEN_HEIGHT // 2 + 80
        bw, bh = 260, 52
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
        # Particles
        if int(self.time * 10) % 3 == 0:
            import random
            self._particles.append({
                "x": random.randint(0, S.SCREEN_WIDTH),
                "y": S.SCREEN_HEIGHT + 5,
                "vy": random.uniform(-40, -80),
                "vx": random.uniform(-10, 10),
                "life": random.uniform(2, 5),
                "size": random.randint(2, 5),
                "color": random.choice([S.COLOR_ACCENT, S.COLOR_ACCENT2,
                                        (255, 200, 150)])
            })
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def draw(self, surface: pygame.Surface):
        surface.fill(S.COLOR_BG)

        # Particles
        for p in self._particles:
            pygame.draw.circle(surface, p["color"],
                               (int(p["x"]), int(p["y"])), p["size"])

        # Title
        title_surf = render_text("Bunny Lords", S.FONT_TITLE,
                                 S.COLOR_ACCENT, bold=True)
        title_rect = title_surf.get_rect(
            center=(S.SCREEN_WIDTH // 2,
                    S.SCREEN_HEIGHT // 2 - 160))
        surface.blit(title_surf, title_rect)

        # Subtitle
        sub_surf = render_text("A Kingdom of Fluff & Strategy", S.FONT_MD,
                               S.COLOR_TEXT_DIM)
        sub_rect = sub_surf.get_rect(
            center=(S.SCREEN_WIDTH // 2, title_rect.bottom + 10))
        surface.blit(sub_surf, sub_rect)

        # Bouncing bunny
        bounce_y = math.sin(self.time * 2.5) * 12
        bunny_rect = pygame.Rect(0, 0, 100, 100)
        bunny_rect.center = (S.SCREEN_WIDTH // 2,
                             S.SCREEN_HEIGHT // 2 - 40 + int(bounce_y))
        draw_bunny_icon(surface, bunny_rect, S.COLOR_WHITE)

        # Buttons
        for btn in self._buttons:
            bc = S.COLOR_BUTTON_HOVER if btn["hover"] else btn["color"]
            draw_rounded_panel(surface, btn["rect"], bc,
                               border_color=S.COLOR_WHITE, radius=12, alpha=240)
            bt = render_text(btn["text"], S.FONT_LG, S.COLOR_WHITE, bold=True)
            br = bt.get_rect(center=btn["rect"].center)
            surface.blit(bt, br)

        # Version
        ver = render_text("v1.0 — Bunny Lords", S.FONT_SM, S.COLOR_TEXT_DIM)
        surface.blit(ver, (10, S.SCREEN_HEIGHT - 26))

    # ── Actions ──────────────────────────────────────────
    def _new_game(self):
        """Start a fresh game by resetting all progress."""
        # Delete existing save files to start completely fresh
        saves = list_saves()
        for save in saves:
            delete_save(save["path"])
        
        # Access base_view state and reset it
        base_state = self.game.state_manager._registry.get("base_view")
        if base_state:
            base_state.reset_to_new_game()  # type: ignore[attr-defined]
        self.game.state_manager.transition_to("base_view")

    def _continue_game(self):
        """Load the most recent save and start."""
        saves = list_saves()
        if saves:
            # Access base_view state to load into
            base_state = self.game.state_manager._registry.get("base_view")
            if base_state:
                load_game(base_state, saves[0]["path"])  # type: ignore[arg-type]
        self.game.state_manager.transition_to("base_view")

    def _open_settings(self):
        self._sm.play("click")
        self.game.state_manager.push("settings")

    def _open_help(self):
        self._sm.play("click")
        self.game.state_manager.push("help_screen")
