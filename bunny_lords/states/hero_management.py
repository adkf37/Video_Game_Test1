"""
Hero Management — Full screen for viewing heroes, stats, equipment, and abilities.

Supports custom hero portraits: place PNG files in assets/sprites/heroes/
named by hero ID (e.g., knight.png, archer.png). Falls back to procedural
bunnies if custom art not found.
"""
from __future__ import annotations
import pygame
import math

from core.state_machine import GameState
from entities.heroes import (Hero, HeroDef, EquipmentDef, Inventory,
                             EQUIP_SLOTS, RARITY_COLORS, load_hero_defs,
                             load_equip_defs)
from utils.asset_loader import render_text
from utils.draw_helpers import (draw_rounded_panel, draw_progress_bar,
                                draw_bunny_icon)
import settings as S


class HeroManagementState(GameState):
    """Screen showing the hero roster, detail view, and equipment management."""

    def __init__(self, game):
        super().__init__(game)
        self.hero_defs = load_hero_defs()
        self.equip_defs = load_equip_defs()

        # Create heroes — one of each defined hero
        self.heroes: list[Hero] = []
        self.inventory = Inventory()

        # Give starter equipment
        self._initialized = False

        # UI state
        self._selected_idx = 0
        self._hover_slot: str | None = None
        self._equip_picker_open = False
        self._equip_picker_slot: str | None = None
        self._equip_picker_items: list[EquipmentDef] = []
        self._equip_hover_idx = -1
        self._time = 0.0
        self._tab = "stats"  # "stats" or "abilities"

        # Back button
        self._back_btn = pygame.Rect(16, S.SCREEN_HEIGHT - 56, 110, 40)
        self._back_hover = False

        # Tab buttons
        self._stats_tab_btn = pygame.Rect(0, 0, 90, 32)
        self._abilities_tab_btn = pygame.Rect(0, 0, 90, 32)

        # Hero selector arrows
        self._left_arrow = pygame.Rect(0, 0, 40, 40)
        self._right_arrow = pygame.Rect(0, 0, 40, 40)

        # Add XP button (for testing / demo)
        self._xp_btn = pygame.Rect(0, 0, 100, 32)

    def _ensure_init(self):
        if self._initialized:
            return
        self._initialized = True
        for hid, hdef in self.hero_defs.items():
            self.heroes.append(Hero(hdef, level=1))

        # Give some starter items to inventory
        starter_items = ["wooden_sword", "leather_vest", "iron_helm",
                         "speed_boots", "iron_sword", "chainmail",
                         "lucky_clover"]
        for eid in starter_items:
            edef = self.equip_defs.get(eid)
            if edef:
                self.inventory.add(edef)

    def enter(self, **params):
        self._ensure_init()
        self._equip_picker_open = False
        self._time = 0.0

    def handle_event(self, event: pygame.event.Event):
        # Equipment picker takes priority
        if self._equip_picker_open:
            if self._handle_equip_picker(event):
                return

        if event.type == pygame.MOUSEMOTION:
            self._back_hover = self._back_btn.collidepoint(event.pos)
            # Check equipment slot hovers
            self._hover_slot = None
            hero = self._current_hero()
            if hero:
                for i, slot in enumerate(EQUIP_SLOTS):
                    sr = self._slot_rect(i)
                    if sr.collidepoint(event.pos):
                        self._hover_slot = slot

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._back_btn.collidepoint(event.pos):
                self.game.state_manager.pop()
                return

            # Hero arrows
            if self._left_arrow.collidepoint(event.pos):
                self._selected_idx = (self._selected_idx - 1) % len(self.heroes)
                return
            if self._right_arrow.collidepoint(event.pos):
                self._selected_idx = (self._selected_idx + 1) % len(self.heroes)
                return

            # Tab buttons
            if self._stats_tab_btn.collidepoint(event.pos):
                self._tab = "stats"
                return
            if self._abilities_tab_btn.collidepoint(event.pos):
                self._tab = "abilities"
                return

            # XP button
            if self._xp_btn.collidepoint(event.pos):
                hero = self._current_hero()
                if hero:
                    lvls = hero.add_xp(50)
                    if lvls > 0:
                        pass  # could show animation
                return

            # Equipment slots
            hero = self._current_hero()
            if hero:
                for i, slot in enumerate(EQUIP_SLOTS):
                    sr = self._slot_rect(i)
                    if sr.collidepoint(event.pos):
                        if hero.equipment[slot]:
                            # Unequip
                            item = hero.unequip(slot)
                            if item:
                                self.inventory.add(item)
                        else:
                            # Open picker
                            self._open_equip_picker(slot)
                        return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self._equip_picker_open:
                    self._equip_picker_open = False
                else:
                    self.game.state_manager.pop()
            if event.key == pygame.K_LEFT:
                self._selected_idx = (self._selected_idx - 1) % len(self.heroes)
            if event.key == pygame.K_RIGHT:
                self._selected_idx = (self._selected_idx + 1) % len(self.heroes)

    def _handle_equip_picker(self, event: pygame.event.Event) -> bool:
        picker_rect = self._equip_picker_rect()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self._equip_picker_open = False
            return True
        if event.type == pygame.MOUSEMOTION:
            if picker_rect.collidepoint(event.pos):
                rel_y = event.pos[1] - picker_rect.y - 40
                self._equip_hover_idx = rel_y // 44
                return True
            self._equip_hover_idx = -1
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not picker_rect.collidepoint(event.pos):
                self._equip_picker_open = False
                return True
            rel_y = event.pos[1] - picker_rect.y - 40
            idx = rel_y // 44
            if 0 <= idx < len(self._equip_picker_items):
                item = self._equip_picker_items[idx]
                hero = self._current_hero()
                if hero:
                    old = hero.equip(item)
                    self.inventory.remove(item)
                    if old:
                        self.inventory.add(old)
                self._equip_picker_open = False
                return True
        return False

    def update(self, dt: float):
        self._time += dt

    def draw(self, surface: pygame.Surface):
        surface.fill(S.COLOR_BG)
        hero = self._current_hero()
        if not hero:
            surface.blit(render_text("No heroes available.", S.FONT_LG,
                                     S.COLOR_TEXT),
                         (S.SCREEN_WIDTH // 2 - 100, S.SCREEN_HEIGHT // 2))
            return

        # ── Left side: Hero portrait + selector ──────────
        self._draw_hero_portrait(surface, hero)

        # ── Right side: Stats or abilities tab ───────────
        self._draw_detail_panel(surface, hero)

        # ── Equipment slots (bottom-left) ────────────────
        self._draw_equipment(surface, hero)

        # ── Equipment picker overlay ─────────────────────
        if self._equip_picker_open:
            self._draw_equip_picker(surface)

        # ── Back button ──────────────────────────────────
        back_clr = S.COLOR_BUTTON_HOVER if self._back_hover else (80, 80, 100)
        draw_rounded_panel(surface, self._back_btn, back_clr,
                           border_color=S.COLOR_WHITE, radius=8, alpha=230)
        bt = render_text("← Back", S.FONT_SM, S.COLOR_WHITE, bold=True)
        surface.blit(bt, (self._back_btn.x + 20, self._back_btn.y + 10))

    # ══════════════════════════════════════════════════════
    #  Drawing helpers
    # ══════════════════════════════════════════════════════
    def _draw_hero_portrait(self, surface: pygame.Surface, hero: Hero):
        # Panel background - large to fit 600x400 portrait
        panel = pygame.Rect(20, 20, 640, 520)
        draw_rounded_panel(surface, panel, S.COLOR_PANEL,
                           border_color=hero.color, radius=10, alpha=235)

        # Hero selector arrows at top
        self._left_arrow.center = (panel.x + 40, panel.y + 25)
        self._right_arrow.center = (panel.right - 40, panel.y + 25)
        pygame.draw.polygon(surface, S.COLOR_TEXT,
                            [(self._left_arrow.centerx + 8, self._left_arrow.y + 5),
                             (self._left_arrow.centerx - 8, self._left_arrow.centery),
                             (self._left_arrow.centerx + 8, self._left_arrow.bottom - 5)])
        pygame.draw.polygon(surface, S.COLOR_TEXT,
                            [(self._right_arrow.centerx - 8, self._right_arrow.y + 5),
                             (self._right_arrow.centerx + 8, self._right_arrow.centery),
                             (self._right_arrow.centerx - 8, self._right_arrow.bottom - 5)])

        # Hero name + title at top center
        name_surf = render_text(hero.name, S.FONT_LG, hero.color, bold=True)
        surface.blit(name_surf, (panel.centerx - name_surf.get_width() // 2,
                                 panel.y + 8))
        title_surf = render_text(f'"{hero.title}"', S.FONT_SM, S.COLOR_TEXT_DIM)
        surface.blit(title_surf, (panel.centerx - title_surf.get_width() // 2,
                                  panel.y + 35))

        # Large bouncing portrait (600x400) - centered
        bounce = math.sin(self._time * 2) * 6
        bunny_rect = pygame.Rect(0, 0, 350, 500)
        bunny_rect.center = (panel.centerx, panel.y + 260 + int(bounce))
        
        # Try loading custom hero portrait
        custom_image = None
        try:
            import os
            # Use absolute path relative to this file's directory
            base_dir = os.path.dirname(os.path.dirname(__file__))
            portrait_path = os.path.join(base_dir, "assets", "sprites", "heroes", f"{hero.id}.png")
            if os.path.exists(portrait_path):
                custom_image = pygame.image.load(portrait_path)
                # Scale to fit bunny_rect
                custom_image = pygame.transform.scale(custom_image, 
                                                      (bunny_rect.width, bunny_rect.height))
        except Exception as e:
            # Print error for debugging
            print(f"Could not load portrait for {hero.id}: {e}")
        
        if custom_image:
            surface.blit(custom_image, bunny_rect)
        else:
            draw_bunny_icon(surface, bunny_rect, hero.color)

        # Role badge below portrait
        role_colors = {"tank": (100, 180, 220), "dps": (220, 100, 100),
                       "support": (100, 220, 140)}
        rc = role_colors.get(hero.role, S.COLOR_TEXT_DIM)
        role_surf = render_text(hero.role.upper(), S.FONT_SM, rc, bold=True)
        rx = panel.centerx - role_surf.get_width() // 2
        surface.blit(role_surf, (rx, panel.y + 465))

        # Level + XP at bottom
        y = panel.y + 485
        level_surf = render_text(f"Level {hero.level}", S.FONT_SM,
                                 S.COLOR_ACCENT, bold=True)
        surface.blit(level_surf, (panel.x + 15, y))
        
        # Power on right
        pwr = render_text(f"Power: {hero.power}", S.FONT_SM,
                          S.COLOR_ACCENT2, bold=True)
        surface.blit(pwr, (panel.right - pwr.get_width() - 15, y))

    def _draw_detail_panel(self, surface: pygame.Surface, hero: Hero):
        panel = pygame.Rect(680, 20, S.SCREEN_WIDTH - 700, 520)
        draw_rounded_panel(surface, panel, S.COLOR_PANEL,
                           border_color=S.COLOR_GRID_LINE, radius=10, alpha=235)

        # Tab buttons
        self._stats_tab_btn.topleft = (panel.x + 10, panel.y + 10)
        self._abilities_tab_btn.topleft = (panel.x + 110, panel.y + 10)

        for btn, label, key in [(self._stats_tab_btn, "Stats", "stats"),
                                (self._abilities_tab_btn, "Abilities", "abilities")]:
            active = self._tab == key
            clr = S.COLOR_ACCENT if active else S.COLOR_PANEL_LIGHT
            draw_rounded_panel(surface, btn, clr, radius=6, alpha=230)
            tc = S.COLOR_WHITE if active else S.COLOR_TEXT_DIM
            t = render_text(label, S.FONT_SM, tc, bold=active)
            surface.blit(t, (btn.x + (btn.width - t.get_width()) // 2,
                             btn.y + 7))

        y = panel.y + 54

        if self._tab == "stats":
            self._draw_stats_tab(surface, hero, panel.x + 20, y, panel.width - 40)
        else:
            self._draw_abilities_tab(surface, hero, panel.x + 20, y, panel.width - 40)

    def _draw_stats_tab(self, surface, hero, x, y, width):
        stats = hero.total_stats
        base = hero.base_stats
        gear = hero.gear_stats

        stat_names = {"hp": "HP", "atk": "Attack", "def": "Defense", "speed": "Speed"}
        stat_colors = {"hp": S.COLOR_HP_GREEN, "atk": S.COLOR_DANGER,
                       "def": S.COLOR_BUTTON, "speed": S.COLOR_ACCENT}

        for key, label in stat_names.items():
            total = stats.get(key, 0)
            base_val = base.get(key, 0)
            gear_val = gear.get(key, 0)

            surface.blit(render_text(label, S.FONT_SM, S.COLOR_TEXT), (x, y))
            # Stat bar
            max_val = 300  # visual max for bar
            bar_w = width - 200
            bar = pygame.Rect(x + 80, y + 2, bar_w, 16)
            pct = min(total / max_val, 1.0)
            draw_progress_bar(surface, bar, pct,
                              fg_color=stat_colors.get(key, S.COLOR_ACCENT),
                              bg_color=S.COLOR_PANEL_LIGHT)

            # Values
            val_str = f"{int(total)}"
            if gear_val > 0:
                val_str += f"  (+{int(gear_val)})"
            val_surf = render_text(val_str, S.FONT_SM, S.COLOR_TEXT)
            surface.blit(val_surf, (x + 90 + bar_w, y))
            y += 30

        # Description
        y += 10
        surface.blit(render_text(hero.definition.description, S.FONT_SM - 2,
                                 S.COLOR_TEXT_DIM), (x, y))

    def _draw_abilities_tab(self, surface, hero, x, y, width):
        abilities = hero.definition.abilities
        for ab in abilities:
            unlocked = ab.get("unlock_level", 1) <= hero.level
            clr = S.COLOR_TEXT if unlocked else S.COLOR_TEXT_DIM

            name_str = ab["name"]
            if not unlocked:
                name_str += f"  (Lv.{ab['unlock_level']})"
            surface.blit(render_text(name_str, S.FONT_SM, clr, bold=unlocked),
                         (x, y))
            y += 20

            desc_clr = S.COLOR_TEXT_DIM if unlocked else (100, 100, 110)
            surface.blit(render_text(ab["description"], S.FONT_SM - 3, desc_clr),
                         (x + 10, y))
            y += 24

            if unlocked and "damage_mult" in ab:
                dm = render_text(f"Damage: ×{ab['damage_mult']}", S.FONT_SM - 3,
                                 S.COLOR_ACCENT)
                surface.blit(dm, (x + 10, y))
                y += 16

            y += 10

    def _draw_equipment(self, surface: pygame.Surface, hero: Hero):
        panel = pygame.Rect(20, 560, S.SCREEN_WIDTH - 40, S.SCREEN_HEIGHT - 620)
        draw_rounded_panel(surface, panel, S.COLOR_PANEL,
                           border_color=S.COLOR_GRID_LINE, radius=10, alpha=235)

        surface.blit(render_text("Equipment  (click to equip/unequip)",
                                 S.FONT_SM, S.COLOR_ACCENT, bold=True),
                     (panel.x + 12, panel.y + 10))

        for i, slot in enumerate(EQUIP_SLOTS):
            sr = self._slot_rect(i)
            equipped = hero.equipment.get(slot)
            is_hover = self._hover_slot == slot

            # Slot background
            bg = S.COLOR_PANEL_LIGHT if is_hover else S.COLOR_BG
            border = S.COLOR_ACCENT if is_hover else S.COLOR_GRID_LINE
            draw_rounded_panel(surface, sr, bg, border_color=border,
                               radius=8, alpha=220)

            # Slot label
            surface.blit(render_text(slot.capitalize(), S.FONT_SM - 2,
                                     S.COLOR_TEXT_DIM),
                         (sr.x + 8, sr.y + 4))

            if equipped:
                # Item name (colored by rarity)
                rc = RARITY_COLORS.get(equipped.rarity, S.COLOR_TEXT)
                surface.blit(render_text(equipped.name, S.FONT_SM, rc, bold=True),
                             (sr.x + 8, sr.y + 22))
                # Stats
                stats_str = "  ".join(f"+{int(v)} {k.upper()}"
                                      for k, v in equipped.stats.items())
                surface.blit(render_text(stats_str, S.FONT_SM - 3,
                                         S.COLOR_TEXT_DIM),
                             (sr.x + 8, sr.y + 42))
                # Rarity
                surface.blit(render_text(equipped.rarity.capitalize(),
                                         S.FONT_SM - 3, rc),
                             (sr.right - 80, sr.y + 4))
            else:
                surface.blit(render_text("— Empty —", S.FONT_SM - 2,
                                         S.COLOR_TEXT_DIM),
                             (sr.x + 8, sr.y + 28))

        # Inventory summary
        inv_x = panel.x + 12
        inv_y = panel.bottom - 28
        inv_count = len(self.inventory.items)
        surface.blit(render_text(f"Inventory: {inv_count} items", S.FONT_SM - 2,
                                 S.COLOR_TEXT_DIM), (inv_x, inv_y))

    def _draw_equip_picker(self, surface: pygame.Surface):
        # Dim
        dim = pygame.Surface((S.SCREEN_WIDTH, S.SCREEN_HEIGHT), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 100))
        surface.blit(dim, (0, 0))

        pr = self._equip_picker_rect()
        draw_rounded_panel(surface, pr, S.COLOR_PANEL,
                           border_color=S.COLOR_ACCENT, radius=10, alpha=245)

        x, y = pr.x + 12, pr.y + 10
        slot_name = self._equip_picker_slot or ""
        surface.blit(render_text(f"Select {slot_name.capitalize()}", S.FONT_MD,
                                 S.COLOR_ACCENT, bold=True), (x, y))
        y += 34

        if not self._equip_picker_items:
            surface.blit(render_text("No items available for this slot.",
                                     S.FONT_SM, S.COLOR_TEXT_DIM), (x, y))
        else:
            for i, item in enumerate(self._equip_picker_items):
                iy = y + i * 44
                bg = S.COLOR_PANEL_LIGHT if i == self._equip_hover_idx else S.COLOR_PANEL
                ir = pygame.Rect(pr.x + 6, iy, pr.width - 12, 40)
                draw_rounded_panel(surface, ir, bg, radius=5, alpha=220)

                rc = RARITY_COLORS.get(item.rarity, S.COLOR_TEXT)
                surface.blit(render_text(item.name, S.FONT_SM, rc, bold=True),
                             (ir.x + 8, ir.y + 2))
                stats_str = "  ".join(f"+{int(v)} {k}" for k, v in item.stats.items())
                surface.blit(render_text(stats_str, S.FONT_SM - 3,
                                         S.COLOR_TEXT_DIM),
                             (ir.x + 8, ir.y + 20))
                surface.blit(render_text(item.rarity.capitalize(), S.FONT_SM - 3,
                                         rc),
                             (ir.right - 80, ir.y + 2))

    # ══════════════════════════════════════════════════════
    #  Helpers
    # ══════════════════════════════════════════════════════
    def _current_hero(self) -> Hero | None:
        if 0 <= self._selected_idx < len(self.heroes):
            return self.heroes[self._selected_idx]
        return None

    def _slot_rect(self, index: int) -> pygame.Rect:
        panel_x = 20
        panel_y = 560
        slot_w = (S.SCREEN_WIDTH - 60) // len(EQUIP_SLOTS)
        return pygame.Rect(panel_x + 12 + index * (slot_w + 4),
                           panel_y + 34, slot_w - 8, 64)

    def _open_equip_picker(self, slot: str):
        self._equip_picker_slot = slot
        self._equip_picker_items = self.inventory.get_by_slot(slot)
        self._equip_picker_open = bool(self._equip_picker_items)
        self._equip_hover_idx = -1

    def _equip_picker_rect(self) -> pygame.Rect:
        count = max(len(self._equip_picker_items), 1)
        h = 50 + count * 44
        return pygame.Rect(S.SCREEN_WIDTH // 2 - 180,
                           S.SCREEN_HEIGHT // 2 - h // 2,
                           360, h)
