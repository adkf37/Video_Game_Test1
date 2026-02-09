"""
Victory Animation — Celebratory dancing bunny overlay after upgrades/completions.
"""
from __future__ import annotations
import pygame
import math
import random
from core.state_machine import GameState
from utils.asset_loader import render_text
from utils.draw_helpers import draw_bunny_icon, draw_rounded_panel
import settings as S


class VictoryAnimationState(GameState):
    """Short auto-dismissing animation overlay with dancing bunny."""

    IS_OVERLAY = True
    DURATION = 2.5  # seconds before auto-close

    def __init__(self, game):
        super().__init__(game)
        self.timer = 0.0
        self.message = ""
        self._particles: list[dict] = []
        self._bunny_rotation = 0.0

    def enter(self, **params):
        self.timer = 0.0
        self.message = params.get("message", "Success!")
        self._particles.clear()
        self._bunny_rotation = 0.0
        # Spawn initial burst of particles
        for _ in range(40):
            self._spawn_particle()

    def handle_event(self, event: pygame.event.Event):
        # Click anywhere to dismiss early
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.game.state_manager.pop()

    def update(self, dt: float):
        self.timer += dt
        self._bunny_rotation += dt * 360  # full rotation per second

        # Auto-dismiss after duration
        if self.timer >= self.DURATION:
            self.game.state_manager.pop()
            return

        # Spawn particles continuously
        if random.random() < 0.3:
            self._spawn_particle()

        # Update particles
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 150 * dt  # gravity
            p["rotation"] += p["vr"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

    def draw(self, surface: pygame.Surface):
        # Semi-transparent overlay
        overlay = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 100))
        surface.blit(overlay, (0, 0))

        # Particles behind bunny
        for p in self._particles:
            alpha = min(1.0, p["life"] / p["max_life"])
            color = (*p["color"], int(255 * alpha))
            # Draw as a rotated rectangle for confetti effect
            size = int(p["size"] * (0.5 + 0.5 * alpha))
            particle_surf = pygame.Surface((size * 2, size), pygame.SRCALPHA)
            pygame.draw.rect(particle_surf, color, (0, 0, size * 2, size), border_radius=2)
            # Rotate
            rotated = pygame.transform.rotate(particle_surf, p["rotation"])
            rect = rotated.get_rect(center=(int(p["x"]), int(p["y"])))
            surface.blit(rotated, rect)

        # Dancing bunny in center
        bunny_size = 200
        bunny_y_offset = math.sin(self.timer * 8) * 20  # bounce
        bunny_scale = 1.0 + math.sin(self.timer * 6) * 0.1  # pulse
        bunny_rect = pygame.Rect(
            0, 0,
            int(bunny_size * bunny_scale),
            int(bunny_size * bunny_scale)
        )
        bunny_rect.center = (
            S.SCREEN_WIDTH // 2,
            S.SCREEN_HEIGHT // 2 - 40 + int(bunny_y_offset)
        )
        
        # Draw bunny with rotation effect (via skew/transform)
        bunny_surf = pygame.Surface((bunny_rect.width, bunny_rect.height), pygame.SRCALPHA)
        draw_bunny_icon(bunny_surf,
                        pygame.Rect(0, 0, bunny_rect.width, bunny_rect.height),
                        S.COLOR_ACCENT2)
        # Simple tilt effect
        tilt = math.sin(self.timer * 10) * 15
        tilted = pygame.transform.rotate(bunny_surf, tilt)
        tilt_rect = tilted.get_rect(center=bunny_rect.center)
        surface.blit(tilted, tilt_rect)

        # Message text
        msg_surf = render_text(self.message, S.FONT_XL, S.COLOR_ACCENT, bold=True)
        # Pulse the message
        msg_scale = 1.0 + math.sin(self.timer * 4) * 0.05
        scaled_msg = pygame.transform.smoothscale(
            msg_surf,
            (int(msg_surf.get_width() * msg_scale),
             int(msg_surf.get_height() * msg_scale))
        )
        msg_rect = scaled_msg.get_rect(
            center=(S.SCREEN_WIDTH // 2, S.SCREEN_HEIGHT // 2 + 140)
        )
        surface.blit(scaled_msg, msg_rect)

        # "Click to continue" hint
        hint = render_text("(click to continue)", S.FONT_SM - 2, S.COLOR_TEXT_DIM)
        surface.blit(hint,
                     (S.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                      S.SCREEN_HEIGHT // 2 + 190))

    def _spawn_particle(self):
        """Spawn a confetti particle."""
        cx, cy = S.SCREEN_WIDTH // 2, S.SCREEN_HEIGHT // 2 - 50
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(100, 300)
        self._particles.append({
            "x": cx + random.uniform(-50, 50),
            "y": cy + random.uniform(-50, 50),
            "vx": math.cos(angle) * speed,
            "vy": math.sin(angle) * speed - random.uniform(100, 200),
            "rotation": random.uniform(0, 360),
            "vr": random.uniform(-360, 360),  # rotation speed
            "size": random.uniform(6, 14),
            "life": random.uniform(1.5, 2.5),
            "max_life": 2.5,
            "color": random.choice([
                S.COLOR_ACCENT,
                S.COLOR_ACCENT2,
                (255, 100, 255),
                (100, 200, 255),
                (255, 255, 100),
                (100, 255, 100),
            ])
        })
