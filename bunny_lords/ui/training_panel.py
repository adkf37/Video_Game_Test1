"""
Training Panel — UI overlay for the barracks troop training screen.
"""
from __future__ import annotations
import pygame
from utils.asset_loader import render_text
from utils.draw_helpers import draw_rounded_panel, draw_progress_bar, draw_bunny_icon
import settings as S


class TrainingPanel:
    """Full-screen-ish overlay for troop training at the barracks."""

    WIDTH = 520
    HEIGHT = 540

    def __init__(self, troop_defs, training_system, resource_mgr,
                 on_close, on_toast):
        self.troop_defs = troop_defs
        self.training_system = training_system
        self.resource_mgr = resource_mgr
        self.on_close = on_close
        self.on_toast = on_toast  # callback(text, color)
        self.visible = False
        self.barracks_level = 1
        self.speed_mult = 1.0

        self.rect = pygame.Rect(
            (S.SCREEN_WIDTH - self.WIDTH) // 2,
            (S.SCREEN_HEIGHT - self.HEIGHT) // 2,
            self.WIDTH, self.HEIGHT)

        self._close_btn = pygame.Rect(0, 0, 30, 30)
        self._hover_idx = -1
        self._hover_close = False
        self._scroll_y = 0
        self._train_count = 5  # default batch size
        # +/- buttons for count
        self._minus_btn = pygame.Rect(0, 0, 30, 28)
        self._plus_btn = pygame.Rect(0, 0, 30, 28)

    def show(self, barracks_level: int, speed_mult: float = 1.0):
        self.visible = True
        self.barracks_level = barracks_level
        self.speed_mult = speed_mult
        self._scroll_y = 0
        self._hover_idx = -1

    def hide(self):
        self.visible = False

    def _available_troops(self) -> list:
        result = []
        for tid, tdef in self.troop_defs.items():
            if tdef.requires_barracks_level <= self.barracks_level:
                result.append(tdef)
        result.sort(key=lambda t: (t.tier, t.name))
        return result

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True

        if event.type == pygame.MOUSEMOTION:
            self._hover_close = self._close_btn.collidepoint(event.pos)
            if self.rect.collidepoint(event.pos):
                list_top = self.rect.y + 100
                rel_y = event.pos[1] - list_top + self._scroll_y
                self._hover_idx = rel_y // 64
                return True
            else:
                self._hover_idx = -1

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_btn.collidepoint(event.pos):
                self.hide()
                return True
            if self._minus_btn.collidepoint(event.pos):
                self._train_count = max(1, self._train_count - 5)
                return True
            if self._plus_btn.collidepoint(event.pos):
                self._train_count = min(100, self._train_count + 5)
                return True
            # Check troop train buttons
            troops = self._available_troops()
            list_top = self.rect.y + 100
            for i, tdef in enumerate(troops):
                item_y = list_top + i * 64 - self._scroll_y
                train_btn = pygame.Rect(self.rect.right - 90, item_y + 8,
                                        70, 40)
                if train_btn.collidepoint(event.pos):
                    ok = self.training_system.start_training(
                        tdef.id, self._train_count, self.speed_mult)
                    if ok:
                        self.on_toast(
                            f"Training {self._train_count}x {tdef.name}!",
                            S.COLOR_ACCENT2)
                    else:
                        can, reason = self.training_system.can_train(
                            tdef.id, self._train_count)
                        self.on_toast(reason or "Cannot train!", S.COLOR_DANGER)
                    return True
            # Check queue cancel buttons
            queue_top = self.rect.y + self.HEIGHT - 150
            for i in range(len(self.training_system.queue)):
                cancel_btn = pygame.Rect(self.rect.right - 70,
                                         queue_top + 6 + i * 32, 50, 24)
                if cancel_btn.collidepoint(event.pos):
                    self.training_system.cancel_job(i)
                    self.on_toast("Training cancelled, resources refunded.",
                                  S.COLOR_ACCENT)
                    return True
            if self.rect.collidepoint(event.pos):
                return True

        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(
                pygame.mouse.get_pos()):
            self._scroll_y = max(0, self._scroll_y - event.y * 30)
            return True

        return False

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        # Dim background
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 120))
        surface.blit(dim, (0, 0))

        draw_rounded_panel(surface, self.rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=10, alpha=245)

        x, y = self.rect.x + 16, self.rect.y + 12

        # Close
        self._close_btn.topleft = (self.rect.right - 36, self.rect.y + 8)
        clr = S.COLOR_DANGER if self._hover_close else S.COLOR_TEXT_DIM
        surface.blit(render_text("✕", S.FONT_MD, clr, bold=True),
                     self._close_btn.topleft)

        # Title
        surface.blit(render_text("⚔ Barracks — Train Troops", S.FONT_LG,
                                 S.COLOR_ACCENT, bold=True), (x, y))
        y += 40

        # Batch size selector
        surface.blit(render_text("Batch:", S.FONT_SM, S.COLOR_TEXT), (x, y + 4))
        self._minus_btn.topleft = (x + 60, y)
        self._plus_btn.topleft = (x + 140, y)
        draw_rounded_panel(surface, self._minus_btn, S.COLOR_BUTTON,
                           radius=5, alpha=220)
        surface.blit(render_text("-5", S.FONT_SM, S.COLOR_WHITE, bold=True),
                     (self._minus_btn.x + 6, self._minus_btn.y + 4))
        cnt_txt = render_text(str(self._train_count), S.FONT_MD,
                              S.COLOR_ACCENT, bold=True)
        surface.blit(cnt_txt, (x + 100, y))
        draw_rounded_panel(surface, self._plus_btn, S.COLOR_BUTTON,
                           radius=5, alpha=220)
        surface.blit(render_text("+5", S.FONT_SM, S.COLOR_WHITE, bold=True),
                     (self._plus_btn.x + 4, self._plus_btn.y + 4))
        y += 36

        # Troop list
        troops = self._available_troops()
        list_top = y
        list_height = self.HEIGHT - 150 - (y - self.rect.y)
        clip_rect = pygame.Rect(self.rect.x, list_top,
                                self.WIDTH, list_height)
        old_clip = surface.get_clip()
        surface.set_clip(clip_rect)

        for i, tdef in enumerate(troops):
            item_y = list_top + i * 64 - self._scroll_y
            item_rect = pygame.Rect(self.rect.x + 8, item_y,
                                    self.WIDTH - 16, 58)
            bg = S.COLOR_PANEL_LIGHT if i == self._hover_idx else S.COLOR_PANEL
            draw_rounded_panel(surface, item_rect, bg, radius=5, alpha=220)

            # Bunny icon (colored by type)
            icon_rect = pygame.Rect(item_rect.x + 4, item_rect.y + 4, 50, 50)
            draw_bunny_icon(surface, icon_rect, tdef.color)

            # Name + tier
            surface.blit(
                render_text(f"{tdef.name}  (T{tdef.tier})", S.FONT_SM,
                            S.COLOR_TEXT, bold=True),
                (item_rect.x + 58, item_rect.y + 4))

            # Stats
            stat_str = f"HP:{tdef.stats['hp']}  ATK:{tdef.stats['atk']}  DEF:{tdef.stats['def']}  SPD:{tdef.stats['speed']}"
            surface.blit(render_text(stat_str, S.FONT_SM - 3, S.COLOR_TEXT_DIM),
                         (item_rect.x + 58, item_rect.y + 22))

            # Cost
            cost_parts = [f"{r[:3]}:{amt * self._train_count}"
                          for r, amt in tdef.cost.items()]
            total_cost = {r: amt * self._train_count for r, amt in tdef.cost.items()}
            can_afford = self.resource_mgr.can_afford(total_cost)
            cost_color = S.COLOR_ACCENT2 if can_afford else S.COLOR_DANGER
            surface.blit(render_text("  ".join(cost_parts), S.FONT_SM - 3,
                                     cost_color),
                         (item_rect.x + 58, item_rect.y + 38))

            # Train button
            train_btn = pygame.Rect(item_rect.right - 78, item_rect.y + 10,
                                    70, 36)
            btn_clr = S.COLOR_BUTTON if can_afford else (70, 70, 80)
            draw_rounded_panel(surface, train_btn, btn_clr, radius=6, alpha=230)
            surface.blit(
                render_text("Train", S.FONT_SM, S.COLOR_WHITE, bold=True),
                (train_btn.x + 12, train_btn.y + 8))

        surface.set_clip(old_clip)

        # ── Training queue ───────────────────────────────
        queue_top = self.rect.y + self.HEIGHT - 145
        pygame.draw.line(surface, S.COLOR_GRID_LINE,
                         (self.rect.x + 10, queue_top - 4),
                         (self.rect.right - 10, queue_top - 4), 1)
        surface.blit(render_text("Training Queue", S.FONT_SM, S.COLOR_ACCENT,
                                 bold=True),
                     (self.rect.x + 16, queue_top))
        queue_top += 20

        if not self.training_system.queue:
            surface.blit(render_text("Queue empty — select troops above.",
                                     S.FONT_SM - 2, S.COLOR_TEXT_DIM),
                         (self.rect.x + 16, queue_top + 4))
        else:
            for i, job in enumerate(self.training_system.queue):
                jy = queue_top + i * 32
                if jy > self.rect.bottom - 20:
                    break
                # Name + progress
                label = f"{job.troop_def.name} ×{job.total_count}"
                if i == 0:
                    label += f"  ({job.trained_count}/{job.total_count})"
                surface.blit(render_text(label, S.FONT_SM - 2, S.COLOR_TEXT),
                             (self.rect.x + 16, jy + 2))
                # Progress bar (only for active job)
                if i == 0:
                    bar = pygame.Rect(self.rect.x + 16, jy + 18,
                                      self.WIDTH - 120, 8)
                    draw_progress_bar(surface, bar, job.progress,
                                      fg_color=S.COLOR_ACCENT2)
                # Cancel button
                cancel_btn = pygame.Rect(self.rect.right - 70, jy + 2, 50, 24)
                draw_rounded_panel(surface, cancel_btn, S.COLOR_DANGER,
                                   radius=4, alpha=200)
                surface.blit(render_text("✕", S.FONT_SM - 2, S.COLOR_WHITE,
                                         bold=True),
                             (cancel_btn.x + 18, cancel_btn.y + 3))


class ArmyOverviewPanel:
    """Side panel showing current army composition and total power."""

    WIDTH = 300
    HEIGHT = 400

    def __init__(self, army, troop_defs, on_close):
        self.army = army
        self.troop_defs = troop_defs
        self.on_close = on_close
        self.visible = False
        self.rect = pygame.Rect(S.SCREEN_WIDTH - self.WIDTH - 10,
                                S.SCREEN_HEIGHT - self.HEIGHT - 70,
                                self.WIDTH, self.HEIGHT)
        self._close_btn = pygame.Rect(0, 0, 30, 30)
        self._hover_close = False
        self._scroll_y = 0

    def show(self):
        self.visible = True
        self._scroll_y = 0

    def hide(self):
        self.visible = False

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible:
            return False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.hide()
            return True
        if event.type == pygame.MOUSEMOTION:
            self._hover_close = self._close_btn.collidepoint(event.pos)
            if self.rect.collidepoint(event.pos):
                return True
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._close_btn.collidepoint(event.pos):
                self.hide()
                return True
            if self.rect.collidepoint(event.pos):
                return True
        if event.type == pygame.MOUSEWHEEL and self.rect.collidepoint(
                pygame.mouse.get_pos()):
            self._scroll_y = max(0, self._scroll_y - event.y * 25)
            return True
        return False

    def draw(self, surface: pygame.Surface):
        if not self.visible:
            return

        draw_rounded_panel(surface, self.rect, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT2, radius=8, alpha=240)
        x, y = self.rect.x + 12, self.rect.y + 10

        # Close
        self._close_btn.topleft = (self.rect.right - 36, self.rect.y + 8)
        clr = S.COLOR_DANGER if self._hover_close else S.COLOR_TEXT_DIM
        surface.blit(render_text("✕", S.FONT_MD, clr, bold=True),
                     self._close_btn.topleft)

        # Title
        surface.blit(render_text("🐰 Army Overview", S.FONT_MD,
                                 S.COLOR_ACCENT2, bold=True), (x, y))
        y += 30

        # Total
        total = self.army.total_count
        power = self.army.total_power(self.troop_defs)
        surface.blit(render_text(f"Total Troops: {total}", S.FONT_SM,
                                 S.COLOR_TEXT), (x, y))
        y += 20
        surface.blit(render_text(f"Army Power: {power}", S.FONT_SM,
                                 S.COLOR_ACCENT, bold=True), (x, y))
        y += 28

        pygame.draw.line(surface, S.COLOR_GRID_LINE, (x, y), (self.rect.right - 12, y), 1)
        y += 8

        # Troop list
        clip = surface.get_clip()
        surface.set_clip(pygame.Rect(self.rect.x, y, self.WIDTH,
                                      self.rect.bottom - y - 8))

        for tid, count in sorted(self.army.troops.items()):
            tdef = self.troop_defs.get(tid)
            if not tdef or count <= 0:
                continue
            iy = y - self._scroll_y
            # Mini bunny icon
            icon_r = pygame.Rect(x, iy, 36, 36)
            draw_bunny_icon(surface, icon_r, tdef.color)
            # Name + count
            surface.blit(render_text(f"{tdef.name}", S.FONT_SM, S.COLOR_TEXT,
                                     bold=True),
                         (x + 42, iy))
            surface.blit(render_text(f"×{count}  (T{tdef.tier} {tdef.type})",
                                     S.FONT_SM - 3, S.COLOR_TEXT_DIM),
                         (x + 42, iy + 18))
            y += 42

        surface.set_clip(clip)

        if self.army.total_count == 0:
            surface.blit(render_text("No troops yet. Train some at the Barracks!",
                                     S.FONT_SM - 2, S.COLOR_TEXT_DIM),
                         (x, self.rect.y + 120))
