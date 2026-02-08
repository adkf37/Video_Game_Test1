"""
Pause Menu — overlay with Resume, Save, Settings, and Quit buttons.
"""
from __future__ import annotations
import pygame
from core.state_machine import GameState
from systems.sound_manager import get_sound_manager
from systems.save_system import save_game
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel
from ui.widgets import Button
import settings as S


class PauseMenuState(GameState):
    """Semi-transparent overlay pause menu."""

    IS_OVERLAY = True

    def __init__(self, game):
        super().__init__(game)
        self._sm = get_sound_manager()

        pw, ph = 320, 360
        px = (S.SCREEN_WIDTH - pw) // 2
        py = (S.SCREEN_HEIGHT - ph) // 2
        self.panel_rect = pygame.Rect(px, py, pw, ph)

        bw, bh = 220, 44
        bx = px + (pw - bw) // 2
        gap = 56

        self._resume_btn = Button(
            pygame.Rect(bx, py + 80, bw, bh),
            "Resume", self._on_resume, color=S.COLOR_ACCENT2
        )
        self._save_btn = Button(
            pygame.Rect(bx, py + 80 + gap, bw, bh),
            "Save Game", self._on_save, color=S.COLOR_BUTTON
        )
        self._settings_btn = Button(
            pygame.Rect(bx, py + 80 + gap * 2, bw, bh),
            "Settings", self._on_settings, color=(120, 120, 160)
        )
        self._quit_btn = Button(
            pygame.Rect(bx, py + 80 + gap * 3, bw, bh),
            "Quit to Menu", self._on_quit, color=S.COLOR_DANGER
        )

        self._buttons = [self._resume_btn, self._save_btn,
                         self._settings_btn, self._quit_btn]
        self._saved_flash = 0.0
        self._base_view = None

    def enter(self, **params):
        self._saved_flash = 0.0
        self._base_view = params.get("base_view")

    def handle_event(self, event: pygame.event.Event):
        for btn in self._buttons:
            if btn.handle_event(event):
                return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_resume()

    def update(self, dt: float):
        if self._saved_flash > 0:
            self._saved_flash -= dt

    def draw(self, surface: pygame.Surface):
        # Dim
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 160))
        surface.blit(dim, (0, 0))

        draw_rounded_panel(surface, self.panel_rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=14, alpha=245)

        # Title
        title = render_text("Paused", S.FONT_XL, S.COLOR_ACCENT, bold=True)
        surface.blit(title,
                     (self.panel_rect.centerx - title.get_width() // 2,
                      self.panel_rect.y + 20))

        for btn in self._buttons:
            btn.draw(surface)

        # Saved flash
        if self._saved_flash > 0:
            alpha = min(1.0, self._saved_flash / 0.5)
            st = render_text("Game Saved!", S.FONT_MD, S.COLOR_ACCENT2, bold=True)
            st.set_alpha(int(255 * alpha))
            surface.blit(st,
                         (self.panel_rect.centerx - st.get_width() // 2,
                          self.panel_rect.bottom - 48))

    def _on_resume(self):
        self._sm.play("click")
        self.game.state_manager.pop()

    def _on_save(self):
        self._sm.play("save")
        if self._base_view:
            save_game(self._base_view, "manual_save")
        self._saved_flash = 2.0

    def _on_settings(self):
        self._sm.play("click")
        self.game.state_manager.push("settings")

    def _on_quit(self):
        self._sm.play("click")
        # Auto-save before quitting
        if self._base_view:
            save_game(self._base_view, "autosave")
        # Pop pause menu + whatever is below, go to main menu
        self.game.state_manager.pop()  # pop pause
        self.game.state_manager.replace("main_menu")
