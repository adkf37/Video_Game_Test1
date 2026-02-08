"""
Quest Panel — overlay UI showing achievement and daily quests.

Shows quest progress, claimable rewards, and categories.
"""
from __future__ import annotations
import pygame

from systems.quest_system import QuestSystem, Quest
from systems.sound_manager import get_sound_manager
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel, draw_progress_bar
from ui.widgets import Button
import settings as S


CATEGORY_TABS = [
    ("achievement", "Achievements", S.COLOR_ACCENT),
    ("daily", "Daily", S.COLOR_ACCENT2),
]


class QuestPanel:
    """Overlay panel showing all quests with progress and claim buttons."""

    def __init__(self, quest_system: QuestSystem, on_close, on_toast):
        self.quest_system = quest_system
        self.on_close = on_close
        self.on_toast = on_toast
        self.visible = False

        self._panel_rect = pygame.Rect(80, 50,
                                       S.SCREEN_WIDTH - 160,
                                       S.SCREEN_HEIGHT - 100)
        self._active_tab = "achievement"
        self._scroll_y = 0
        self._hover_idx = -1

        self._close_btn = Button(
            pygame.Rect(self._panel_rect.right - 46,
                        self._panel_rect.y + 6, 36, 36),
            "X", self._do_close,
            color=S.COLOR_DANGER
        )

    def show(self):
        self.visible = True
        self._scroll_y = 0
        self._hover_idx = -1

    def hide(self):
        self.visible = False

    def _do_close(self):
        self.hide()
        self.on_close()

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if self._close_btn.handle_event(event):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not self._panel_rect.collidepoint(mx, my):
                self._do_close()
                return True

            # Tab clicks
            tab_x = self._panel_rect.x + 16
            tab_y = self._panel_rect.y + 46
            for cat_id, cat_name, cat_color in CATEGORY_TABS:
                tab_rect = pygame.Rect(tab_x, tab_y, 120, 28)
                if tab_rect.collidepoint(mx, my):
                    self._active_tab = cat_id
                    self._scroll_y = 0
                    return True
                tab_x += 130

            # Quest claim clicks
            quests = self._get_quests()
            item_y_start = self._panel_rect.y + 90 - self._scroll_y
            for i, q in enumerate(quests):
                iy = item_y_start + i * 76
                claim_rect = pygame.Rect(
                    self._panel_rect.right - 120, iy + 10, 90, 30)
                if claim_rect.collidepoint(mx, my) and q.is_complete and not q.claimed:
                    if self.quest_system.claim(q.id):
                        rew_parts = [f"+{amt} {r}" for r, amt in
                                     q.definition.rewards.items()]
                        self.on_toast(f"Claimed: {', '.join(rew_parts)}",
                                      S.COLOR_ACCENT2)
                        get_sound_manager().play("quest_complete")
                    return True
            return True

        if event.type == pygame.MOUSEWHEEL and self._panel_rect.collidepoint(
                *pygame.mouse.get_pos()):
            self._scroll_y = max(0, self._scroll_y - event.y * 30)
            return True

        if event.type == pygame.MOUSEMOTION:
            if self._panel_rect.collidepoint(event.pos):
                quests = self._get_quests()
                item_y_start = self._panel_rect.y + 90 - self._scroll_y
                self._hover_idx = -1
                for i in range(len(quests)):
                    iy = item_y_start + i * 76
                    item_rect = pygame.Rect(self._panel_rect.x + 16, iy,
                                            self._panel_rect.width - 32, 70)
                    if item_rect.collidepoint(event.pos):
                        self._hover_idx = i
                        break
                return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._do_close()
            return True

        return False

    def _get_quests(self) -> list[Quest]:
        if self._active_tab == "achievement":
            return self.quest_system.get_achievements()
        return self.quest_system.get_dailies()

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # Dim background
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        # Panel
        draw_rounded_panel(surface, self._panel_rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=10, alpha=245)

        x, y = self._panel_rect.x + 16, self._panel_rect.y + 10

        # Title
        title = render_text("Quests", S.FONT_LG, S.COLOR_ACCENT, bold=True)
        surface.blit(title, (x, y))

        # Claimable count badge
        claimable = self.quest_system.claimable_count
        if claimable > 0:
            badge = render_text(f"  {claimable} claimable!",
                                S.FONT_SM, S.COLOR_ACCENT2, bold=True)
            surface.blit(badge, (x + title.get_width() + 10, y + 8))

        self._close_btn.draw(surface)

        # Category tabs
        tab_x = self._panel_rect.x + 16
        tab_y = self._panel_rect.y + 46
        for cat_id, cat_name, cat_color in CATEGORY_TABS:
            is_active = cat_id == self._active_tab
            tab_rect = pygame.Rect(tab_x, tab_y, 120, 28)
            bg = cat_color if is_active else S.COLOR_PANEL_LIGHT
            draw_rounded_panel(surface, tab_rect, bg, radius=5,
                               alpha=230 if is_active else 160)
            label = render_text(cat_name, S.FONT_SM - 2,
                                S.COLOR_BLACK if is_active else S.COLOR_TEXT,
                                bold=is_active)
            surface.blit(label, (tab_rect.centerx - label.get_width() // 2,
                                 tab_rect.centery - label.get_height() // 2))
            tab_x += 130

        # Quest list
        quests = self._get_quests()
        clip = surface.get_clip()
        inner = pygame.Rect(self._panel_rect.x,
                            self._panel_rect.y + 82,
                            self._panel_rect.width,
                            self._panel_rect.height - 92)
        surface.set_clip(inner)

        item_y = self._panel_rect.y + 90 - self._scroll_y
        for i, q in enumerate(quests):
            item_rect = pygame.Rect(self._panel_rect.x + 16, item_y,
                                    self._panel_rect.width - 32, 70)

            # Background
            if q.claimed:
                bg = (40, 50, 40)
            elif q.is_complete:
                bg = (50, 60, 40)
            elif i == self._hover_idx:
                bg = S.COLOR_PANEL_LIGHT
            else:
                bg = S.COLOR_PANEL

            draw_rounded_panel(surface, item_rect, bg, radius=6, alpha=220)

            ix, iy = item_rect.x + 10, item_rect.y + 6

            # Quest name
            name_color = (S.COLOR_TEXT_DIM if q.claimed else
                          S.COLOR_ACCENT2 if q.is_complete else S.COLOR_TEXT)
            nt = render_text(q.definition.name, S.FONT_SM, name_color, bold=True)
            surface.blit(nt, (ix, iy))

            # Description
            dt = render_text(q.definition.description, S.FONT_SM - 2,
                             S.COLOR_TEXT_DIM)
            surface.blit(dt, (ix, iy + 22))

            # Progress bar
            bar_rect = pygame.Rect(ix, iy + 42, 200, 10)
            fg = S.COLOR_ACCENT2 if q.is_complete else S.COLOR_ACCENT
            draw_progress_bar(surface, bar_rect, q.progress_pct,
                              fg_color=fg, bg_color=S.COLOR_PANEL_LIGHT)

            # Progress text
            prog_txt = render_text(
                f"{q.progress}/{q.definition.target}",
                S.FONT_SM - 4, S.COLOR_TEXT_DIM)
            surface.blit(prog_txt, (ix + 206, iy + 40))

            # Rewards
            rew_parts = [f"+{amt} {r}" for r, amt in q.definition.rewards.items()]
            rew_txt = render_text("  ".join(rew_parts), S.FONT_SM - 4,
                                  S.COLOR_ACCENT)
            surface.blit(rew_txt, (ix + 280, iy + 6))

            # Claim button / status
            claim_rect = pygame.Rect(
                item_rect.right - 110, iy + 10, 90, 30)
            if q.is_complete and not q.claimed:
                draw_rounded_panel(surface, claim_rect, S.COLOR_ACCENT2,
                                   radius=6, alpha=230)
                ct = render_text("Claim", S.FONT_SM - 2, S.COLOR_BLACK,
                                 bold=True)
                surface.blit(ct, (claim_rect.centerx - ct.get_width() // 2,
                                  claim_rect.centery - ct.get_height() // 2))
            elif q.claimed:
                ct = render_text("Claimed ✓", S.FONT_SM - 2,
                                 S.COLOR_TEXT_DIM)
                surface.blit(ct, (claim_rect.x, claim_rect.y + 4))

            item_y += 76

        surface.set_clip(clip)

        # Empty state
        if not quests:
            et = render_text("No quests in this category",
                             S.FONT_SM, S.COLOR_TEXT_DIM)
            surface.blit(et, (self._panel_rect.centerx - et.get_width() // 2,
                              self._panel_rect.centery))
