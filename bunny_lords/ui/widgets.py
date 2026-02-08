"""
UI Widgets — reusable HUD elements drawn with Pygame primitives.

No dependency on pygame_gui here — these are game-specific custom widgets.
"""
from __future__ import annotations
import pygame
from utils.asset_loader import render_text, get_font
from utils.draw_helpers import (draw_rounded_panel, draw_progress_bar,
                                draw_building_shape, draw_bunny_icon)
import settings as S


# ═══════════════════════════════════════════════════════════
#  Resource Bar (top HUD)
# ═══════════════════════════════════════════════════════════
class ResourceBar:
    """Horizontal bar at the top of the screen showing all resources."""
    HEIGHT = 52

    def __init__(self, resource_mgr):
        self.resource_mgr = resource_mgr
        self.rect = pygame.Rect(0, 0, S.SCREEN_WIDTH, self.HEIGHT)

    def draw(self, surface: pygame.Surface):
        # Background
        draw_rounded_panel(surface, self.rect, S.COLOR_PANEL,
                           border_color=S.COLOR_GRID_LINE, radius=0, alpha=240)

        names = self.resource_mgr.resource_names
        slot_w = S.SCREEN_WIDTH // len(names)
        for i, rid in enumerate(names):
            x = i * slot_w + 16
            y = 8
            color = tuple(S.RESOURCE_COLORS.get(rid, S.COLOR_TEXT))
            amount = self.resource_mgr.get(rid)
            cap = self.resource_mgr.capacity.get(rid, 0)
            rdef = self.resource_mgr.get_def(rid)

            # Icon circle
            pygame.draw.circle(surface, color, (x + 12, self.HEIGHT // 2), 10)
            pygame.draw.circle(surface, S.COLOR_WHITE,
                               (x + 12, self.HEIGHT // 2), 10, 2)

            # Amount text
            amount_str = _format_number(amount)
            cap_str = _format_number(cap)
            txt = render_text(f"{rdef.get('name', rid)}: {amount_str} / {cap_str}",
                              S.FONT_SM, S.COLOR_TEXT)
            surface.blit(txt, (x + 28, y + 2))

            # Mini progress bar
            bar_rect = pygame.Rect(x + 28, y + 24, slot_w - 60, 10)
            pct = amount / cap if cap > 0 else 0
            fg = color if pct < 0.9 else S.COLOR_DANGER
            draw_progress_bar(surface, bar_rect, pct, fg_color=fg,
                              bg_color=S.COLOR_PANEL_LIGHT)


# ═══════════════════════════════════════════════════════════
#  Build Menu Panel (right side)
# ═══════════════════════════════════════════════════════════
class BuildMenuPanel:
    """Slide-in panel listing available buildings to construct."""

    WIDTH = 310
    ITEM_HEIGHT = 70

    def __init__(self, building_defs: dict, resource_mgr, on_select):
        self.building_defs = building_defs
        self.resource_mgr = resource_mgr
        self.on_select = on_select  # callback(building_id)
        self.visible = False
        self.rect = pygame.Rect(S.SCREEN_WIDTH - self.WIDTH, ResourceBar.HEIGHT,
                                self.WIDTH,
                                S.SCREEN_HEIGHT - ResourceBar.HEIGHT)
        self._items: list[str] = []
        self._scroll_y = 0
        self._hover_idx = -1

    def show(self, available_ids: list[str], castle_level: int):
        """Show the panel with buildings available to build."""
        self._items = []
        for bid in available_ids:
            bdef = self.building_defs.get(bid)
            if bdef and bdef.requires_castle <= castle_level:
                self._items.append(bid)
        self.visible = True
        self._scroll_y = 0
        self._hover_idx = -1

    def hide(self):
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.MOUSEMOTION:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y + self._scroll_y
                self._hover_idx = rel_y // self.ITEM_HEIGHT
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                rel_y = event.pos[1] - self.rect.y + self._scroll_y
                idx = rel_y // self.ITEM_HEIGHT
                if 0 <= idx < len(self._items):
                    self.on_select(self._items[idx])
                return True
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(pygame.mouse.get_pos()):
            self._scroll_y = max(0, self._scroll_y - event.y * 30)
            return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return
        draw_rounded_panel(surface, self.rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=6, alpha=235)

        # Title
        title = render_text("Build", S.FONT_LG, S.COLOR_ACCENT, bold=True)
        surface.blit(title, (self.rect.x + 16, self.rect.y + 8))

        # Items
        clip = surface.get_clip()
        inner = pygame.Rect(self.rect.x, self.rect.y + 46,
                            self.rect.width, self.rect.height - 46)
        surface.set_clip(inner)

        for i, bid in enumerate(self._items):
            bdef = self.building_defs[bid]
            item_y = self.rect.y + 46 + i * self.ITEM_HEIGHT - self._scroll_y
            item_rect = pygame.Rect(self.rect.x + 6, item_y,
                                    self.WIDTH - 12, self.ITEM_HEIGHT - 4)
            # Highlight
            bg = S.COLOR_PANEL_LIGHT if i == self._hover_idx else S.COLOR_PANEL
            draw_rounded_panel(surface, item_rect, bg, radius=5, alpha=220)

            # Building icon
            icon_rect = pygame.Rect(item_rect.x + 6, item_rect.y + 6, 48, 48)
            color = S.BUILDING_COLORS.get(bid, S.COLOR_TEXT_DIM)
            draw_building_shape(surface, icon_rect, color, bid)

            # Name
            n = render_text(bdef.name, S.FONT_SM, S.COLOR_TEXT, bold=True)
            surface.blit(n, (item_rect.x + 60, item_rect.y + 6))

            # Cost summary
            cost = bdef.cost_for(1)
            can_afford = self.resource_mgr.can_afford(cost)
            cost_parts = []
            for r, amt in cost.items():
                cost_parts.append(f"{r[:3]}:{int(amt)}")
            cost_str = "  ".join(cost_parts) if cost_parts else "Free"
            cost_color = S.COLOR_ACCENT2 if can_afford else S.COLOR_DANGER
            ct = render_text(cost_str, S.FONT_SM - 2, cost_color)
            surface.blit(ct, (item_rect.x + 60, item_rect.y + 26))

            # Build time
            bt = bdef.build_time_for(1)
            tt = render_text(f"⏱ {_format_time(bt)}", S.FONT_SM - 2, S.COLOR_TEXT_DIM)
            surface.blit(tt, (item_rect.x + 60, item_rect.y + 44))

        surface.set_clip(clip)


# ═══════════════════════════════════════════════════════════
#  Building Info Panel (selected building)
# ═══════════════════════════════════════════════════════════
class BuildingInfoPanel:
    """Panel showing details about a selected / clicked building."""

    WIDTH = 320
    HEIGHT = 320

    def __init__(self, resource_mgr, on_upgrade, on_close):
        self.resource_mgr = resource_mgr
        self.on_upgrade = on_upgrade  # callback(building)
        self.on_close = on_close
        self.visible = False
        self.building: object | None = None
        self.rect = pygame.Rect(S.SCREEN_WIDTH - self.WIDTH - 10,
                                ResourceBar.HEIGHT + 10,
                                self.WIDTH, self.HEIGHT)
        self._upgrade_btn = pygame.Rect(0, 0, 160, 40)
        self._close_btn = pygame.Rect(0, 0, 30, 30)
        self._upgrade_hover = False
        self._close_hover = False

    def show(self, building):
        self.building = building
        self.visible = True

    def hide(self):
        self.visible = False
        self.building = None

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible or not self.building:
            return False
        if event.type == pygame.MOUSEMOTION:
            self._upgrade_hover = self._upgrade_btn.collidepoint(event.pos)
            self._close_hover = self._close_btn.collidepoint(event.pos)
            if self.rect.collidepoint(event.pos):
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_btn.collidepoint(event.pos):
                self.on_close()
                return True
            if self._upgrade_btn.collidepoint(event.pos):
                if self.building and self.building.can_upgrade():
                    self.on_upgrade(self.building)
                return True
            if self.rect.collidepoint(event.pos):
                return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.building:
            return

        b = self.building
        bdef = b.definition

        draw_rounded_panel(surface, self.rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=8, alpha=240)

        x, y = self.rect.x + 12, self.rect.y + 10

        # Close button
        self._close_btn.topleft = (self.rect.right - 36, self.rect.y + 6)
        close_color = S.COLOR_DANGER if self._close_hover else S.COLOR_TEXT_DIM
        ct = render_text("✕", S.FONT_MD, close_color, bold=True)
        surface.blit(ct, self._close_btn.topleft)

        # Building icon + name
        icon_rect = pygame.Rect(x, y, 52, 52)
        color = S.BUILDING_COLORS.get(b.id, S.COLOR_TEXT_DIM)
        draw_building_shape(surface, icon_rect, color, b.id)

        n = render_text(bdef.name, S.FONT_MD, S.COLOR_ACCENT, bold=True)
        surface.blit(n, (x + 60, y))
        lvl = render_text(f"Level {b.level}", S.FONT_SM, S.COLOR_TEXT)
        surface.blit(lvl, (x + 60, y + 26))

        y += 64

        # Description
        desc = render_text(bdef.description, S.FONT_SM - 2, S.COLOR_TEXT_DIM)
        surface.blit(desc, (x, y))
        y += 24

        # Production (if applicable)
        prod = b.production
        if prod:
            prod_str = "  ".join(f"+{v}/s {k}" for k, v in prod.items())
            pt = render_text(f"Produces: {prod_str}", S.FONT_SM, S.COLOR_ACCENT2)
            surface.blit(pt, (x, y))
            y += 22

        # Build progress
        if b.building:
            y += 4
            pt = render_text("Under construction...", S.FONT_SM, S.COLOR_ACCENT)
            surface.blit(pt, (x, y))
            y += 20
            bar = pygame.Rect(x, y, self.WIDTH - 30, 14)
            draw_progress_bar(surface, bar, b.build_progress,
                              fg_color=S.COLOR_ACCENT, border_color=S.COLOR_TEXT_DIM)
            y += 20
            remaining = render_text(f"{_format_time(b.build_timer)} remaining",
                                    S.FONT_SM - 2, S.COLOR_TEXT_DIM)
            surface.blit(remaining, (x, y))
            y += 22

        # Upgrade button
        y += 8
        if b.can_upgrade():
            next_lvl = b.level + 1
            cost = bdef.cost_for(next_lvl)
            can = self.resource_mgr.can_afford(cost)

            # Cost display
            for r, amt in cost.items():
                have = self.resource_mgr.get(r)
                clr = S.COLOR_ACCENT2 if have >= amt else S.COLOR_DANGER
                ct = render_text(f"{r}: {int(amt)}", S.FONT_SM - 2, clr)
                surface.blit(ct, (x, y))
                y += 16
            y += 6

            self._upgrade_btn.topleft = (x, y)
            btn_color = (S.COLOR_BUTTON_HOVER if self._upgrade_hover and can
                         else S.COLOR_BUTTON if can
                         else (80, 80, 90))
            draw_rounded_panel(surface, self._upgrade_btn, btn_color,
                               border_color=S.COLOR_WHITE if can else S.COLOR_TEXT_DIM,
                               radius=8, alpha=230)
            ut = render_text(f"Upgrade to Lv.{next_lvl}", S.FONT_SM,
                             S.COLOR_WHITE if can else S.COLOR_TEXT_DIM, bold=True)
            ur = ut.get_rect(center=self._upgrade_btn.center)
            surface.blit(ut, ur)
        elif not b.building:
            mt = render_text("Max level reached!", S.FONT_SM, S.COLOR_ACCENT)
            surface.blit(mt, (x, y))


# ═══════════════════════════════════════════════════════════
#  Notification Toasts
# ═══════════════════════════════════════════════════════════
class ToastManager:
    """Manages fleeting notification messages."""

    def __init__(self):
        self._toasts: list[dict] = []

    def show(self, text: str, color: tuple = S.COLOR_ACCENT, duration: float = 3.0):
        self._toasts.append({
            "text": text, "color": color,
            "life": duration, "max_life": duration
        })

    def update(self, dt: float):
        for t in self._toasts:
            t["life"] -= dt
        self._toasts = [t for t in self._toasts if t["life"] > 0]

    def draw(self, surface: pygame.Surface):
        y = ResourceBar.HEIGHT + 10
        for t in self._toasts:
            alpha = min(1.0, t["life"] / 0.5)  # fade out in last 0.5s
            txt = render_text(f"  {t['text']}  ", S.FONT_SM, t["color"], bold=True)
            bg_rect = pygame.Rect(S.SCREEN_WIDTH // 2 - txt.get_width() // 2 - 8,
                                  y, txt.get_width() + 16, txt.get_height() + 8)
            draw_rounded_panel(surface, bg_rect, S.COLOR_PANEL,
                               border_color=t["color"], radius=6,
                               alpha=int(200 * alpha))
            txt.set_alpha(int(255 * alpha))
            surface.blit(txt, (bg_rect.x + 8, bg_rect.y + 4))
            y += bg_rect.height + 6


# ═══════════════════════════════════════════════════════════
#  Simple Button
# ═══════════════════════════════════════════════════════════
class Button:
    def __init__(self, rect: pygame.Rect, text: str, callback,
                 color=S.COLOR_BUTTON, text_color=S.COLOR_WHITE):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.color = color
        self.text_color = text_color
        self.hover = False
        self.enabled = True

    def handle_event(self, event: pygame.event.Event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        if (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.hover and self.enabled):
            self.callback()
            return True
        return False

    def draw(self, surface: pygame.Surface):
        c = S.COLOR_BUTTON_HOVER if self.hover else self.color
        if not self.enabled:
            c = (70, 70, 80)
        draw_rounded_panel(surface, self.rect, c,
                           border_color=S.COLOR_WHITE, radius=8, alpha=230)
        txt = render_text(self.text, S.FONT_SM, self.text_color, bold=True)
        tr = txt.get_rect(center=self.rect.center)
        surface.blit(txt, tr)


# ═══════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════
def _format_number(n: float) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.1f}K"
    return f"{int(n)}"


def _format_time(seconds: float) -> str:
    s = max(0, int(seconds))
    if s >= 3600:
        return f"{s // 3600}h {(s % 3600) // 60}m"
    if s >= 60:
        return f"{s // 60}m {s % 60}s"
    return f"{s}s"
