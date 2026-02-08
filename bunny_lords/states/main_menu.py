"""
Main Menu — Title screen with animated bunny and play button.
"""
import pygame
import math
from core.state_machine import GameState
from utils.asset_loader import render_text
from utils.draw_helpers import draw_bunny_icon, draw_rounded_panel
import settings as S


class MainMenuState(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.time = 0.0
        self.btn_rect = pygame.Rect(0, 0, 260, 60)
        self.btn_rect.center = (S.SCREEN_WIDTH // 2, S.SCREEN_HEIGHT // 2 + 100)
        self.btn_hover = False
        self._particles: list[dict] = []

    def enter(self, **params):
        self.time = 0.0

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEMOTION:
            self.btn_hover = self.btn_rect.collidepoint(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.btn_rect.collidepoint(event.pos):
                self.game.state_manager.replace("base_view")

    def update(self, dt: float):
        self.time += dt
        # Spawn subtle particles
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

        # Particles behind everything
        for p in self._particles:
            alpha = min(255, int(180 * (p["life"] / 4.0)))
            r = p["size"]
            pygame.draw.circle(surface, p["color"],
                               (int(p["x"]), int(p["y"])), r)

        # Title
        title_surf = render_text("Bunny Lords", S.FONT_TITLE,
                                 S.COLOR_ACCENT, bold=True)
        title_rect = title_surf.get_rect(
            center=(S.SCREEN_WIDTH // 2,
                    S.SCREEN_HEIGHT // 2 - 140))
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
                             S.SCREEN_HEIGHT // 2 - 20 + int(bounce_y))
        draw_bunny_icon(surface, bunny_rect, S.COLOR_WHITE)

        # Play button
        btn_color = S.COLOR_BUTTON_HOVER if self.btn_hover else S.COLOR_BUTTON
        draw_rounded_panel(surface, self.btn_rect, btn_color,
                           border_color=S.COLOR_WHITE, radius=12, alpha=240)
        btn_text = render_text("Play", S.FONT_LG, S.COLOR_WHITE, bold=True)
        btn_text_rect = btn_text.get_rect(center=self.btn_rect.center)
        surface.blit(btn_text, btn_text_rect)

        # Version
        ver = render_text("v0.1 — Phase 1", S.FONT_SM, S.COLOR_TEXT_DIM)
        surface.blit(ver, (10, S.SCREEN_HEIGHT - 26))
