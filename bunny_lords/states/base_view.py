"""
Base View — The main base-building screen.

Shows an 8×8 grid with placed buildings, resource bar HUD, and panels for
building new structures and upgrading existing ones.
"""
from __future__ import annotations
import pygame

from core.state_machine import GameState
from core.event_bus import EventBus
from entities.buildings import Building, load_building_defs, BuildingDef
from systems.resource_system import ResourceManager
from ui.widgets import (ResourceBar, BuildMenuPanel, BuildingInfoPanel,
                        ToastManager, Button)
from utils.asset_loader import render_text
from utils.draw_helpers import (draw_rounded_panel, draw_building_shape,
                                draw_progress_bar, draw_bunny_icon)
import settings as S


class BaseViewState(GameState):
    def __init__(self, game):
        super().__init__(game)

        # ── Data ─────────────────────────────────────────
        self.building_defs = load_building_defs()
        self.resource_mgr = ResourceManager()
        self.event_bus: EventBus = game.event_bus

        # Grid: 2D array, None = empty, Building = occupied
        self.grid: list[list[Building | None]] = [
            [None] * S.GRID_COLS for _ in range(S.GRID_ROWS)
        ]
        self.buildings: list[Building] = []

        # ── Timers ───────────────────────────────────────
        self.resource_tick_timer = 0.0

        # ── UI layers ───────────────────────────────────
        self.resource_bar = ResourceBar(self.resource_mgr)
        self.build_menu = BuildMenuPanel(
            self.building_defs, self.resource_mgr,
            on_select=self._on_build_menu_select
        )
        self.info_panel = BuildingInfoPanel(
            self.resource_mgr,
            on_upgrade=self._on_upgrade,
            on_close=self._close_info
        )
        self.toasts = ToastManager()

        # Build button (bottom-right, opens menu)
        self._build_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 140, S.SCREEN_HEIGHT - 60, 120, 44),
            "🔨 Build", self._toggle_build_menu,
            color=S.COLOR_ACCENT
        )
        # Back to menu button
        self._menu_btn = Button(
            pygame.Rect(10, S.SCREEN_HEIGHT - 60, 100, 44),
            "Menu", lambda: self.game.state_manager.replace("main_menu"),
            color=(80, 80, 100)
        )

        # ── Selection state ──────────────────────────────
        self._selected_cell: tuple[int, int] | None = None  # grid coords
        self._hover_cell: tuple[int, int] | None = None
        self._placing: str | None = None  # building_id being placed

        # ── Particles (build complete sparkle) ───────────
        self._particles: list[dict] = []

    # ══════════════════════════════════════════════════════
    #  Lifecycle
    # ══════════════════════════════════════════════════════
    def enter(self, **params):
        # Place the starting castle at center
        if not self.buildings:
            self._place_building("castle", S.GRID_COLS // 2 - 1,
                                 S.GRID_ROWS // 2 - 1, instant=True)

    # ══════════════════════════════════════════════════════
    #  Events
    # ══════════════════════════════════════════════════════
    def handle_event(self, event: pygame.event.Event):
        # UI panels consume events first
        if self.info_panel.handle_event(event):
            return
        if self.build_menu.handle_event(event):
            return
        if self._build_btn.handle_event(event):
            return
        if self._menu_btn.handle_event(event):
            return

        if event.type == pygame.MOUSEMOTION:
            self._hover_cell = self._screen_to_grid(event.pos)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            cell = self._screen_to_grid(event.pos)
            if cell:
                gx, gy = cell
                if self._placing:
                    self._try_place(gx, gy)
                else:
                    occupant = self.grid[gy][gx]
                    if occupant:
                        self._select_building(occupant)
                    else:
                        self._selected_cell = cell
                        self.info_panel.hide()
        # Right-click cancels placement / closes panels
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self._placing = None
            self.build_menu.hide()
            self.info_panel.hide()

        # Keyboard shortcuts
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._placing = None
                self.build_menu.hide()
                self.info_panel.hide()
            if event.key == pygame.K_b:
                self._toggle_build_menu()

    # ══════════════════════════════════════════════════════
    #  Update
    # ══════════════════════════════════════════════════════
    def update(self, dt: float):
        # Resource production tick
        self.resource_tick_timer += dt
        if self.resource_tick_timer >= S.RESOURCE_TICK:
            self.resource_tick_timer -= S.RESOURCE_TICK
            self.resource_mgr.apply_production(self.buildings)

        # Building timers
        for b in self.buildings:
            completed = b.update(dt)
            if completed:
                self.toasts.show(f"{b.name} Level {b.level} complete!",
                                 S.COLOR_ACCENT2)
                self.event_bus.emit("building_complete",
                                    building_id=b.id, level=b.level)
                self._spawn_particles(b.grid_x, b.grid_y, count=20)
                # Refresh info panel if this building is selected
                if (self.info_panel.visible and
                        self.info_panel.building is b):
                    self.info_panel.show(b)

        # Particles
        for p in self._particles:
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["life"] -= dt
        self._particles = [p for p in self._particles if p["life"] > 0]

        self.toasts.update(dt)

    # ══════════════════════════════════════════════════════
    #  Draw
    # ══════════════════════════════════════════════════════
    def draw(self, surface: pygame.Surface):
        surface.fill(S.COLOR_BG)

        self._draw_grid(surface)
        self._draw_buildings(surface)
        self._draw_particles(surface)

        # HUD
        self.resource_bar.draw(surface)
        self.build_menu.draw(surface)
        self.info_panel.draw(surface)
        self.toasts.draw(surface)
        self._build_btn.draw(surface)
        self._menu_btn.draw(surface)

        # Placement ghost
        if self._placing and self._hover_cell:
            gx, gy = self._hover_cell
            rect = self._grid_to_screen(gx, gy)
            color = S.BUILDING_COLORS.get(self._placing, S.COLOR_TEXT_DIM)
            ghost = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            draw_building_shape(ghost,
                                pygame.Rect(0, 0, rect.width, rect.height),
                                color, self._placing)
            ghost.set_alpha(140)
            surface.blit(ghost, rect.topleft)

        # Castle level indicator
        castle = self._get_castle()
        if castle:
            cl_text = render_text(f"Castle Level {castle.level}",
                                  S.FONT_SM, S.COLOR_ACCENT, bold=True)
            surface.blit(cl_text, (S.SCREEN_WIDTH // 2 - cl_text.get_width() // 2,
                                   S.SCREEN_HEIGHT - 30))

    # ══════════════════════════════════════════════════════
    #  Grid drawing
    # ══════════════════════════════════════════════════════
    def _draw_grid(self, surface: pygame.Surface):
        for gy in range(S.GRID_ROWS):
            for gx in range(S.GRID_COLS):
                rect = self._grid_to_screen(gx, gy)
                # Tile fill
                is_hover = (self._hover_cell == (gx, gy))
                is_selected = (self._selected_cell == (gx, gy))
                if is_hover and self._placing:
                    fill = (*S.COLOR_ACCENT[:3], 40)
                elif is_hover:
                    fill = (*S.COLOR_PANEL_LIGHT[:3], 180)
                elif is_selected:
                    fill = (*S.COLOR_ACCENT[:3], 50)
                else:
                    fill = S.COLOR_GRID_EMPTY

                tile = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                pygame.draw.rect(tile, fill, (0, 0, rect.width, rect.height),
                                 border_radius=4)
                surface.blit(tile, rect.topleft)

                # Grid border
                pygame.draw.rect(surface, S.COLOR_GRID_LINE, rect, width=1,
                                 border_radius=4)

    def _draw_buildings(self, surface: pygame.Surface):
        for b in self.buildings:
            rect = self._grid_to_screen(b.grid_x, b.grid_y)
            color = S.BUILDING_COLORS.get(b.id, S.COLOR_TEXT_DIM)

            # Dim if under construction
            if b.building:
                color = tuple(c // 2 for c in color)

            draw_building_shape(surface, rect, color, b.id)

            # Level badge
            badge_txt = render_text(str(b.level), S.FONT_SM - 2, S.COLOR_WHITE,
                                    bold=True)
            bx = rect.right - badge_txt.get_width() - 4
            by = rect.y + 2
            pygame.draw.circle(surface, S.COLOR_PANEL,
                               (bx + badge_txt.get_width() // 2,
                                by + badge_txt.get_height() // 2),
                               max(badge_txt.get_width(), badge_txt.get_height()) // 2 + 3)
            surface.blit(badge_txt, (bx, by))

            # Construction progress bar
            if b.building:
                bar_rect = pygame.Rect(rect.x + 4, rect.bottom - 10,
                                       rect.width - 8, 6)
                draw_progress_bar(surface, bar_rect, b.build_progress,
                                  fg_color=S.COLOR_ACCENT)

    def _draw_particles(self, surface: pygame.Surface):
        for p in self._particles:
            a = min(255, int(200 * (p["life"] / p["max_life"])))
            pygame.draw.circle(surface, p["color"],
                               (int(p["x"]), int(p["y"])), max(1, int(p["size"])))

    # ══════════════════════════════════════════════════════
    #  Grid helpers
    # ══════════════════════════════════════════════════════
    def _grid_to_screen(self, gx: int, gy: int) -> pygame.Rect:
        x = S.GRID_OFFSET_X + gx * S.TILE_SIZE
        y = S.GRID_OFFSET_Y + gy * S.TILE_SIZE
        return pygame.Rect(x, y, S.TILE_SIZE, S.TILE_SIZE)

    def _screen_to_grid(self, pos: tuple[int, int]) -> tuple[int, int] | None:
        mx, my = pos
        gx = (mx - S.GRID_OFFSET_X) // S.TILE_SIZE
        gy = (my - S.GRID_OFFSET_Y) // S.TILE_SIZE
        if 0 <= gx < S.GRID_COLS and 0 <= gy < S.GRID_ROWS:
            return (gx, gy)
        return None

    # ══════════════════════════════════════════════════════
    #  Building logic
    # ══════════════════════════════════════════════════════
    def _place_building(self, bid: str, gx: int, gy: int,
                        instant: bool = False) -> Building | None:
        bdef = self.building_defs.get(bid)
        if not bdef:
            return None
        b = Building(bdef, gx, gy, level=0 if not instant else 1)
        if not instant:
            cost = bdef.cost_for(1)
            if not self.resource_mgr.pay(cost):
                self.toasts.show("Not enough resources!", S.COLOR_DANGER)
                return None
            bt = bdef.build_time_for(1)
            b.start_build(1, bt)
        self.grid[gy][gx] = b
        self.buildings.append(b)
        self._placing = None
        self.build_menu.hide()
        if not instant:
            self.toasts.show(f"Building {bdef.name}...", S.COLOR_ACCENT)
        return b

    def _try_place(self, gx: int, gy: int):
        if self.grid[gy][gx] is not None:
            self.toasts.show("Tile occupied!", S.COLOR_DANGER)
            return
        bid = self._placing
        bdef = self.building_defs.get(bid)
        if bdef and bdef.unique:
            # Check if already placed
            for b in self.buildings:
                if b.id == bid:
                    self.toasts.show(f"{bdef.name} already built!", S.COLOR_DANGER)
                    return
        self._place_building(bid, gx, gy)

    def _on_upgrade(self, building: Building):
        if not building.can_upgrade():
            return
        next_lvl = building.level + 1
        cost = building.definition.cost_for(next_lvl)
        if not self.resource_mgr.pay(cost):
            self.toasts.show("Not enough resources!", S.COLOR_DANGER)
            return
        bt = building.definition.build_time_for(next_lvl)
        building.start_build(next_lvl, bt)
        self.toasts.show(f"Upgrading {building.name} to Lv.{next_lvl}...",
                         S.COLOR_ACCENT)
        self.info_panel.show(building)

    def _select_building(self, building: Building):
        self.info_panel.show(building)
        self._selected_cell = (building.grid_x, building.grid_y)

    def _close_info(self):
        self.info_panel.hide()
        self._selected_cell = None

    def _toggle_build_menu(self):
        if self.build_menu.visible:
            self.build_menu.hide()
            self._placing = None
        else:
            castle = self._get_castle()
            castle_lvl = castle.level if castle else 1
            # Gather all unlocked building IDs
            unlocked = set()
            for lvl in range(1, castle_lvl + 1):
                data = self.building_defs["castle"].get_level_data(lvl)
                if data and "unlocks" in data:
                    unlocked.update(data["unlocks"])
            self.build_menu.show(list(unlocked), castle_lvl)
            self.info_panel.hide()

    def _on_build_menu_select(self, building_id: str):
        """User picked a building from the menu — enter placement mode."""
        bdef = self.building_defs.get(building_id)
        if not bdef:
            return

        # Check if unique and already placed
        if bdef.unique:
            for b in self.buildings:
                if b.id == building_id:
                    self.toasts.show(f"{bdef.name} already built!", S.COLOR_DANGER)
                    return

        # Check affordability
        cost = bdef.cost_for(1)
        if not self.resource_mgr.can_afford(cost):
            self.toasts.show("Not enough resources!", S.COLOR_DANGER)
            return

        self._placing = building_id
        self.build_menu.hide()
        self.toasts.show(f"Click a tile to place {bdef.name}", S.COLOR_ACCENT2, 4.0)

    def _get_castle(self) -> Building | None:
        for b in self.buildings:
            if b.id == "castle":
                return b
        return None

    def _spawn_particles(self, gx: int, gy: int, count: int = 15):
        import random
        rect = self._grid_to_screen(gx, gy)
        cx, cy = rect.center
        for _ in range(count):
            self._particles.append({
                "x": cx + random.randint(-20, 20),
                "y": cy + random.randint(-20, 20),
                "vx": random.uniform(-60, 60),
                "vy": random.uniform(-100, -30),
                "life": random.uniform(0.5, 1.5),
                "max_life": 1.5,
                "size": random.uniform(2, 5),
                "color": random.choice([S.COLOR_ACCENT, S.COLOR_ACCENT2,
                                        S.COLOR_WHITE])
            })
