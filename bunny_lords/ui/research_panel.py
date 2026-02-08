"""
Research Panel — overlay UI for the research tree.

Shows research categories (tabs), available/completed nodes, progress bar,
and handles starting/cancelling research.
"""
from __future__ import annotations
import pygame

from systems.research_system import ResearchSystem, ResearchDef
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel, draw_progress_bar
from ui.widgets import Button
import settings as S


# Category display config
CATEGORY_COLORS = {
    "economy":  (255, 200, 80),
    "military": (220, 80, 80),
    "defense":  (120, 180, 220),
    "hero":     (180, 140, 255),
}
CATEGORY_ICONS = {
    "economy":  "ECO",
    "military": "MIL",
    "defense":  "DEF",
    "hero":     "HRO",
}


class ResearchPanel:
    """Full-screen overlay panel for the research tree."""

    def __init__(self, research_system: ResearchSystem, resource_mgr,
                 on_close, on_toast):
        self.research = research_system
        self.resource_mgr = resource_mgr
        self.on_close = on_close
        self.on_toast = on_toast
        self.visible = False
        self.academy_level = 1

        # Layout
        self._panel_rect = pygame.Rect(60, 40,
                                       S.SCREEN_WIDTH - 120,
                                       S.SCREEN_HEIGHT - 80)
        self._active_cat = "economy"
        self._scroll_y = 0
        self._hover_idx = -1

        # Buttons
        self._close_btn = Button(
            pygame.Rect(self._panel_rect.right - 46,
                        self._panel_rect.y + 6, 36, 36),
            "X", self._do_close,
            color=S.COLOR_DANGER
        )
        self._cancel_btn = Button(
            pygame.Rect(0, 0, 120, 34),
            "Cancel", self._cancel_research,
            color=(180, 80, 80)
        )

    def show(self, academy_level: int):
        self.visible = True
        self.academy_level = academy_level
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

        if self.research.is_researching and self._cancel_btn.handle_event(event):
            return True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if not self._panel_rect.collidepoint(mx, my):
                self._do_close()
                return True

            # Tab clicks
            tab_y = self._panel_rect.y + 50
            tab_x = self._panel_rect.x + 16
            for cat in self.research.categories:
                tab_rect = pygame.Rect(tab_x, tab_y, 80, 30)
                if tab_rect.collidepoint(mx, my):
                    self._active_cat = cat
                    self._scroll_y = 0
                    return True
                tab_x += 90

            # Research item clicks
            items = self.research.get_by_category(self._active_cat)
            item_y_start = self._panel_rect.y + 100 - self._scroll_y
            for i, rdef in enumerate(items):
                item_rect = pygame.Rect(self._panel_rect.x + 16,
                                        item_y_start + i * 66,
                                        self._panel_rect.width - 32, 60)
                if item_rect.collidepoint(mx, my):
                    self._try_start_research(rdef)
                    return True
            return True

        if event.type == pygame.MOUSEWHEEL and self._panel_rect.collidepoint(
                *pygame.mouse.get_pos()):
            self._scroll_y = max(0, self._scroll_y - event.y * 30)
            return True

        if event.type == pygame.MOUSEMOTION:
            if self._panel_rect.collidepoint(event.pos):
                items = self.research.get_by_category(self._active_cat)
                item_y_start = self._panel_rect.y + 100 - self._scroll_y
                self._hover_idx = -1
                for i, rdef in enumerate(items):
                    item_rect = pygame.Rect(self._panel_rect.x + 16,
                                            item_y_start + i * 66,
                                            self._panel_rect.width - 32, 60)
                    if item_rect.collidepoint(event.pos):
                        self._hover_idx = i
                        break
                return True

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._do_close()
            return True

        return False

    def _try_start_research(self, rdef: ResearchDef):
        if self.research.is_researched(rdef.id):
            self.on_toast("Already researched!", S.COLOR_TEXT_DIM)
            return
        ok, reason = self.research.start_research(rdef.id, self.academy_level)
        if ok:
            self.on_toast(f"Researching {rdef.name}...", S.COLOR_ACCENT)
        else:
            self.on_toast(reason, S.COLOR_DANGER)

    def _cancel_research(self):
        if self.research.cancel_research():
            self.on_toast("Research cancelled (50% refund)", S.COLOR_ACCENT)

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # Dim background
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        surface.blit(dim, (0, 0))

        # Main panel
        draw_rounded_panel(surface, self._panel_rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=10, alpha=245)

        x, y = self._panel_rect.x + 16, self._panel_rect.y + 10

        # Title
        title = render_text("Research", S.FONT_LG, S.COLOR_ACCENT, bold=True)
        surface.blit(title, (x, y))

        # Academy level
        alv = render_text(f"Academy Lv.{self.academy_level}",
                          S.FONT_SM, S.COLOR_TEXT_DIM)
        surface.blit(alv, (x + title.get_width() + 20, y + 8))

        # Close button
        self._close_btn.draw(surface)

        # Current research progress
        if self.research.is_researching:
            rdef = self.research.defs.get(self.research.current)
            if rdef:
                prog_y = y + 34
                pt = render_text(f"Researching: {rdef.name}",
                                 S.FONT_SM, S.COLOR_ACCENT2, bold=True)
                surface.blit(pt, (x, prog_y))
                bar = pygame.Rect(x + pt.get_width() + 10, prog_y + 2,
                                  200, 16)
                draw_progress_bar(surface, bar, self.research.progress,
                                  fg_color=S.COLOR_ACCENT2)
                time_left = render_text(f"{int(self.research.timer)}s",
                                        S.FONT_SM - 2, S.COLOR_TEXT_DIM)
                surface.blit(time_left, (bar.right + 6, prog_y + 1))
                # Cancel button
                self._cancel_btn.rect.topleft = (bar.right + 50, prog_y - 2)
                self._cancel_btn.draw(surface)

        # Category tabs
        tab_y = self._panel_rect.y + 50
        tab_x = self._panel_rect.x + 16
        for cat in self.research.categories:
            is_active = cat == self._active_cat
            cat_color = CATEGORY_COLORS.get(cat, S.COLOR_TEXT)
            tab_rect = pygame.Rect(tab_x, tab_y, 80, 28)
            bg = cat_color if is_active else S.COLOR_PANEL_LIGHT
            draw_rounded_panel(surface, tab_rect, bg, radius=5,
                               alpha=230 if is_active else 160)
            label = render_text(cat.capitalize(), S.FONT_SM - 2,
                                S.COLOR_BLACK if is_active else S.COLOR_TEXT,
                                bold=is_active)
            surface.blit(label, (tab_rect.centerx - label.get_width() // 2,
                                 tab_rect.centery - label.get_height() // 2))
            tab_x += 90

        # Research items for active category
        items = self.research.get_by_category(self._active_cat)
        clip = surface.get_clip()
        inner = pygame.Rect(self._panel_rect.x,
                            self._panel_rect.y + 90,
                            self._panel_rect.width,
                            self._panel_rect.height - 100)
        surface.set_clip(inner)

        item_y = self._panel_rect.y + 100 - self._scroll_y
        for i, rdef in enumerate(items):
            item_rect = pygame.Rect(self._panel_rect.x + 16, item_y,
                                    self._panel_rect.width - 32, 60)

            is_done = self.research.is_researched(rdef.id)
            is_avail = self.research.is_available(rdef.id, self.academy_level)
            is_current = self.research.current == rdef.id
            is_hover = i == self._hover_idx

            # Background
            if is_current:
                bg = (60, 80, 60)
            elif is_done:
                bg = (40, 60, 40)
            elif is_hover and is_avail:
                bg = S.COLOR_PANEL_LIGHT
            else:
                bg = S.COLOR_PANEL

            draw_rounded_panel(surface, item_rect, bg, radius=6, alpha=220)

            ix, iy = item_rect.x + 8, item_rect.y + 4

            # Status icon
            if is_done:
                st = render_text("✓", S.FONT_MD, S.COLOR_ACCENT2, bold=True)
                surface.blit(st, (ix, iy + 6))
            elif is_current:
                st = render_text("⏳", S.FONT_MD, S.COLOR_ACCENT)
                surface.blit(st, (ix, iy + 6))
            elif not is_avail:
                st = render_text("🔒", S.FONT_SM, S.COLOR_TEXT_DIM)
                surface.blit(st, (ix + 2, iy + 8))
            else:
                cat_color = CATEGORY_COLORS.get(rdef.category, S.COLOR_TEXT)
                pygame.draw.circle(surface, cat_color,
                                   (ix + 10, iy + 18), 8)

            # Name
            name_color = S.COLOR_ACCENT2 if is_done else (
                S.COLOR_TEXT if is_avail else S.COLOR_TEXT_DIM)
            nt = render_text(rdef.name, S.FONT_SM, name_color, bold=True)
            surface.blit(nt, (ix + 28, iy))

            # Description
            dt = render_text(rdef.description, S.FONT_SM - 2, S.COLOR_TEXT_DIM)
            surface.blit(dt, (ix + 28, iy + 20))

            # Cost & time (right side)
            if not is_done:
                cost_parts = []
                for r, amt in rdef.cost.items():
                    have = self.resource_mgr.get(r)
                    c = S.COLOR_ACCENT2 if have >= amt else S.COLOR_DANGER
                    cp = render_text(f"{r[:3]}:{int(amt)}", S.FONT_SM - 4, c)
                    cost_parts.append(cp)
                cx = item_rect.right - 10
                for cp in reversed(cost_parts):
                    cx -= cp.get_width() + 8
                    surface.blit(cp, (cx, iy + 2))

                tt = render_text(f"{int(rdef.time)}s", S.FONT_SM - 4,
                                 S.COLOR_TEXT_DIM)
                surface.blit(tt, (item_rect.right - tt.get_width() - 10,
                                  iy + 20))

            # Prereqs
            if rdef.requires and not is_done:
                reqs = ", ".join(
                    self.research.defs[r].name
                    for r in rdef.requires if r in self.research.defs)
                if reqs:
                    rt = render_text(f"Requires: {reqs}", S.FONT_SM - 4,
                                     S.COLOR_TEXT_DIM)
                    surface.blit(rt, (ix + 28, iy + 38))

            item_y += 66

        surface.set_clip(clip)
