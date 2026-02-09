"""
Help Screen — Instructions overlay for new players.
"""
from __future__ import annotations
import pygame
from core.state_machine import GameState
from systems.sound_manager import get_sound_manager
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel
from ui.widgets import Button
import settings as S


class HelpScreenState(GameState):
    """Full-screen overlay with game instructions."""

    IS_OVERLAY = True

    def __init__(self, game):
        super().__init__(game)
        self._sm = get_sound_manager()

        pw, ph = 800, 560
        px = (S.SCREEN_WIDTH - pw) // 2
        py = (S.SCREEN_HEIGHT - ph) // 2
        self.panel_rect = pygame.Rect(px, py, pw, ph)

        self._close_btn = Button(
            pygame.Rect(px + pw // 2 - 60, py + ph - 56, 120, 40),
            "Got It!", self._on_close, color=S.COLOR_ACCENT
        )

        self._scroll_y = 0

    def enter(self, **params):
        self._scroll_y = 0

    def handle_event(self, event: pygame.event.Event):
        if self._close_btn.handle_event(event):
            return

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._on_close()
            return

        if event.type == pygame.MOUSEWHEEL:
            self._scroll_y = max(0, self._scroll_y - event.y * 20)

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        # Dim background
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 170))
        surface.blit(dim, (0, 0))

        # Panel
        draw_rounded_panel(surface, self.panel_rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=14, alpha=250)

        # Title
        title = render_text("How to Play", S.FONT_XL, S.COLOR_ACCENT, bold=True)
        surface.blit(title,
                     (self.panel_rect.centerx - title.get_width() // 2,
                      self.panel_rect.y + 20))

        # Content area with scroll
        clip = surface.get_clip()
        content_rect = pygame.Rect(
            self.panel_rect.x + 20,
            self.panel_rect.y + 76,
            self.panel_rect.width - 40,
            self.panel_rect.height - 140
        )
        surface.set_clip(content_rect)

        y = content_rect.y - self._scroll_y

        # Instructions
        instructions = [
            ("GOAL", "Build and upgrade your bunny kingdom, train troops, research tech, complete quests!"),
            ("", ""),
            ("UPGRADING CASTLE", "Your Castle level unlocks new buildings. Upgrade it first!"),
            ("  • Level 1: Carrot Farms, Lumber Burrows"),
            ("  • Level 2: Stone Quarries"),
            ("  • Level 3: Gold Mines, Warehouses"),
            ("  • Level 4: Barracks (train troops!)"),
            ("  • Level 5: Academy (research), Walls"),
            ("", ""),
            ("TROOPS", "Upgrade Castle to Level 4, build Barracks, click it to train troops!"),
            ("", ""),
            ("STONE QUARRIES", "Click stone quarries 5 times every 10 seconds to produce stone!"),
            ("  • They show needing clicks with red status"),
            ("", ""),
            ("KEYBOARD SHORTCUTS", ""),
            ("  • B = Open build menu"),
            ("  • A = View army"),
            ("  • H = Manage heroes"),
            ("  • W = World map (campaign battles)"),
            ("  • Q = View quests"),
            ("  • Esc = Pause menu / Cancel"),
            ("", ""),
            ("QUESTS", ""),
            ("  • Achievements: Claim once, permanent rewards"),
            ("  • Daily Quests: Reset every 24 hours"),
            ("", ""),
            ("HEROES", "Press H to manage heroes. Equip gear to boost stats."),
            ("  • Heroes boost your army in battles"),
            ("  • Level them up with XP button"),
            ("", ""),
            ("BATTLES", "Open World Map (W) to fight campaign stages."),
            ("  • Win stages to get rewards & unlock next"),
            ("", ""),
            ("RESEARCH", "Build Academy (Castle Lv5), click it to research tech."),
            ("  • Research gives permanent bonuses"),
        ]

        for line in instructions:
            if isinstance(line, tuple):
                heading, body = line
                if heading:
                    ht = render_text(heading, S.FONT_SM, S.COLOR_ACCENT, bold=True)
                    surface.blit(ht, (content_rect.x, y))
                    y += 20
                if body:
                    bt = render_text(body, S.FONT_SM - 2, S.COLOR_TEXT)
                    surface.blit(bt, (content_rect.x + 10, y))
                    y += 20
            else:
                lt = render_text(line, S.FONT_SM - 2, S.COLOR_TEXT)
                surface.blit(lt, (content_rect.x + 10, y))
                y += 20

        surface.set_clip(clip)

        # Close button
        self._close_btn.draw(surface)

        # Scroll hint
        if self._scroll_y == 0:
            hint = render_text("Scroll for more...", S.FONT_SM - 4, S.COLOR_TEXT_DIM)
            surface.blit(hint,
                         (self.panel_rect.centerx - hint.get_width() // 2,
                          self.panel_rect.bottom - 80))

    def _on_close(self):
        self._sm.play("click")
        self.game.state_manager.pop()
