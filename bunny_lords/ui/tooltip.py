"""
Tooltip — hover-activated info box that follows the mouse cursor.
"""
from __future__ import annotations
import pygame
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel
import settings as S


class Tooltip:
    """Manages a single floating tooltip that appears on hover."""

    DELAY = 0.35          # seconds before showing
    WIDTH_MAX = 260
    PADDING = 8
    LINE_HEIGHT = 18

    def __init__(self):
        self._text: str = ""
        self._lines: list[str] = []
        self._visible = False
        self._hover_timer = 0.0
        self._mouse_pos = (0, 0)
        self._target_key: str | None = None  # used to reset timer on target change

    def set(self, key: str, text: str, mouse_pos: tuple[int, int]):
        """
        Call every frame while hovering a tooltip-enabled element.
        *key* should uniquely identify the element (e.g. "building_3_4").
        """
        if key != self._target_key:
            # New target — restart delay
            self._target_key = key
            self._hover_timer = 0.0
            self._visible = False
            self._text = text
            self._lines = self._wrap(text)
        self._mouse_pos = mouse_pos

    def clear(self):
        """Call when the mouse is not over any tooltip target."""
        self._target_key = None
        self._visible = False
        self._hover_timer = 0.0

    def update(self, dt: float):
        if self._target_key is not None and not self._visible:
            self._hover_timer += dt
            if self._hover_timer >= self.DELAY:
                self._visible = True

    def draw(self, surface: pygame.Surface):
        if not self._visible or not self._lines:
            return

        # Calculate size
        w = min(self.WIDTH_MAX,
                max(render_text(l, S.FONT_SM - 2, S.COLOR_TEXT).get_width()
                    for l in self._lines) + self.PADDING * 2)
        h = len(self._lines) * self.LINE_HEIGHT + self.PADDING * 2

        # Position: prefer below-right of cursor, clamp to screen
        mx, my = self._mouse_pos
        x = mx + 14
        y = my + 18
        if x + w > S.SCREEN_WIDTH - 4:
            x = mx - w - 4
        if y + h > S.SCREEN_HEIGHT - 4:
            y = my - h - 4

        rect = pygame.Rect(x, y, w, h)
        draw_rounded_panel(surface, rect, (30, 33, 48),
                           border_color=S.COLOR_ACCENT, radius=6, alpha=240)

        ty = y + self.PADDING
        for line in self._lines:
            ts = render_text(line, S.FONT_SM - 2, S.COLOR_TEXT)
            surface.blit(ts, (x + self.PADDING, ty))
            ty += self.LINE_HEIGHT

    # ── Helpers ──────────────────────────────────────────
    def _wrap(self, text: str) -> list[str]:
        """Simple word-wrap."""
        words = text.split()
        lines = []
        current = ""
        for word in words:
            test = f"{current} {word}".strip()
            ts = render_text(test, S.FONT_SM - 2, S.COLOR_TEXT)
            if ts.get_width() > self.WIDTH_MAX - self.PADDING * 2 and current:
                lines.append(current)
                current = word
            else:
                current = test
        if current:
            lines.append(current)
        return lines if lines else [text]
