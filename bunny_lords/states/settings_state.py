"""
Settings State — Options overlay for volume, FPS toggle, etc.
"""
from __future__ import annotations
import pygame
from core.state_machine import GameState
from systems.sound_manager import get_sound_manager
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel, draw_progress_bar
from ui.widgets import Button
import settings as S


class SettingsState(GameState):
    """Full-screen overlay for game settings."""

    IS_OVERLAY = True

    def __init__(self, game):
        super().__init__(game)
        self._sm = get_sound_manager()

        # Overlay dims
        self.panel_w = 460
        self.panel_h = 420
        self.panel_x = (S.SCREEN_WIDTH - self.panel_w) // 2
        self.panel_y = (S.SCREEN_HEIGHT - self.panel_h) // 2
        self.panel_rect = pygame.Rect(self.panel_x, self.panel_y,
                                       self.panel_w, self.panel_h)

        # Sliders
        self._slider_w = 260
        self._slider_h = 14
        self._sliders: list[dict] = []
        self._dragging: int | None = None

        # FPS toggle
        self.show_fps = True

        self._back_btn = Button(
            pygame.Rect(self.panel_x + self.panel_w // 2 - 60,
                        self.panel_y + self.panel_h - 56, 120, 40),
            "Back", self._on_back,
            color=S.COLOR_BUTTON
        )

    def enter(self, **params):
        self.show_fps = self.game.show_fps
        self._build_sliders()

    def _build_sliders(self):
        sx = self.panel_x + 160
        self._sliders = [
            {
                "label": "Master Volume",
                "rect": pygame.Rect(sx, self.panel_y + 90,
                                    self._slider_w, self._slider_h),
                "get": lambda: self._sm.master_volume,
                "set": lambda v: self._sm.set_master_volume(v),
            },
            {
                "label": "SFX Volume",
                "rect": pygame.Rect(sx, self.panel_y + 150,
                                    self._slider_w, self._slider_h),
                "get": lambda: self._sm.sfx_volume,
                "set": lambda v: self._sm.set_sfx_volume(v),
            },
            {
                "label": "Sound Enabled",
                "rect": pygame.Rect(sx, self.panel_y + 210,
                                    self._slider_w, self._slider_h),
                "get": lambda: 1.0 if self._sm.enabled else 0.0,
                "set": lambda v: setattr(self._sm, 'enabled', v > 0.5),
                "toggle": True,
            },
            {
                "label": "Show FPS",
                "rect": pygame.Rect(sx, self.panel_y + 270,
                                    self._slider_w, self._slider_h),
                "get": lambda: 1.0 if self.show_fps else 0.0,
                "set": lambda v: setattr(self, 'show_fps', v > 0.5),
                "toggle": True,
            },
        ]

    def handle_event(self, event: pygame.event.Event):
        if self._back_btn.handle_event(event):
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_back()
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, s in enumerate(self._sliders):
                hit_rect = s["rect"].inflate(0, 16)
                if hit_rect.collidepoint(event.pos):
                    if s.get("toggle"):
                        # Toggle on click
                        cur = s["get"]()
                        s["set"](0.0 if cur > 0.5 else 1.0)
                        self._sm.play("click")
                    else:
                        self._dragging = i
                        self._update_slider(i, event.pos[0])
                    return

        if event.type == pygame.MOUSEMOTION and self._dragging is not None:
            self._update_slider(self._dragging, event.pos[0])

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self._dragging = None

    def _update_slider(self, idx: int, mx: int):
        s = self._sliders[idx]
        r = s["rect"]
        val = max(0.0, min(1.0, (mx - r.x) / r.width))
        s["set"](val)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        # Dim background
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 150))
        surface.blit(dim, (0, 0))

        # Panel
        draw_rounded_panel(surface, self.panel_rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=12, alpha=245)

        # Title
        title = render_text("Settings", S.FONT_LG, S.COLOR_ACCENT, bold=True)
        surface.blit(title,
                     (self.panel_x + self.panel_w // 2 - title.get_width() // 2,
                      self.panel_y + 20))

        # Sliders
        for s in self._sliders:
            label = render_text(s["label"], S.FONT_SM, S.COLOR_TEXT)
            surface.blit(label, (self.panel_x + 24, s["rect"].y - 2))

            if s.get("toggle"):
                # Draw on/off toggle
                val = s["get"]()
                on = val > 0.5
                toggle_rect = pygame.Rect(s["rect"].x, s["rect"].y, 50, 24)
                bg_col = S.COLOR_ACCENT2 if on else (80, 80, 100)
                pygame.draw.rect(surface, bg_col, toggle_rect, border_radius=12)
                knob_x = toggle_rect.x + (28 if on else 2)
                pygame.draw.circle(surface, S.COLOR_WHITE,
                                   (knob_x + 10, toggle_rect.centery), 10)
                state_txt = render_text("ON" if on else "OFF",
                                        S.FONT_SM - 2, S.COLOR_TEXT)
                surface.blit(state_txt,
                             (toggle_rect.right + 10, toggle_rect.y + 2))
            else:
                # Draw slider bar
                val = s["get"]()
                r = s["rect"]
                # Track
                pygame.draw.rect(surface, (60, 65, 90), r, border_radius=4)
                # Fill
                fill_r = pygame.Rect(r.x, r.y, int(r.width * val), r.height)
                pygame.draw.rect(surface, S.COLOR_ACCENT, fill_r, border_radius=4)
                # Knob
                knob_x = r.x + int(r.width * val)
                pygame.draw.circle(surface, S.COLOR_WHITE,
                                   (knob_x, r.centery), 9)
                pygame.draw.circle(surface, S.COLOR_ACCENT,
                                   (knob_x, r.centery), 9, 2)
                # Value label
                pct = render_text(f"{int(val * 100)}%", S.FONT_SM - 2,
                                  S.COLOR_TEXT_DIM)
                surface.blit(pct, (r.right + 10, r.y - 1))

        # Back button
        self._back_btn.draw(surface)

    def _on_back(self):
        self._sm.play("click")
        self.game.show_fps = self.show_fps
        self.game.state_manager.pop()
