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
from entities.troops import Army, load_troop_defs
from entities.heroes import Hero, load_hero_defs, load_equip_defs, Inventory
from systems.resource_system import ResourceManager
from systems.training_system import TrainingSystem
from systems.combat_system import CampaignData
from systems.research_system import ResearchSystem
from systems.quest_system import QuestSystem
from systems.sound_manager import get_sound_manager
from systems.save_system import save_game
from ui.widgets import (ResourceBar, BuildMenuPanel, BuildingInfoPanel,
                        ToastManager, Button)
from ui.training_panel import TrainingPanel, ArmyOverviewPanel
from ui.research_panel import ResearchPanel
from ui.quest_panel import QuestPanel
from ui.tooltip import Tooltip
from utils.asset_loader import render_text
from utils.draw_helpers import (draw_rounded_panel, draw_building_shape,
                                draw_progress_bar, draw_bunny_icon)
import settings as S


class BaseViewState(GameState):
    def __init__(self, game):
        super().__init__(game)

        # ── Data ─────────────────────────────────────────
        self.building_defs = load_building_defs()
        self.troop_defs = load_troop_defs()
        self.resource_mgr = ResourceManager()
        self.event_bus: EventBus = game.event_bus

        # Grid: 2D array, None = empty, Building = occupied
        self.grid: list[list[Building | None]] = [
            [None] * S.GRID_COLS for _ in range(S.GRID_ROWS)
        ]
        self.buildings: list[Building] = []

        # Army & training
        self.army = Army()
        self.training_system = TrainingSystem(
            self.army, self.resource_mgr)

        # Heroes
        self.hero_defs = load_hero_defs()
        self.equip_defs = load_equip_defs()
        self.inventory = Inventory()
        self.heroes: list[Hero] = [
            Hero(hdef) for hdef in self.hero_defs.values()
        ]

        # Campaign / combat
        self.campaign = CampaignData()

        # Research
        self.research_system = ResearchSystem(self.resource_mgr)

        # Quests
        self.quest_system = QuestSystem(self.resource_mgr, self.event_bus)

        # ── Timers ───────────────────────────────────────
        self.resource_tick_timer = 0.0
        self.autosave_timer = 0.0

        # ── Sound / Tooltip ──────────────────────────────
        self._sm = get_sound_manager()
        self.tooltip = Tooltip()

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
        self.training_panel = TrainingPanel(
            self.troop_defs, self.training_system, self.resource_mgr,
            on_close=lambda: self.training_panel.hide(),
            on_toast=lambda text, color: self.toasts.show(text, color)
        )
        self.army_panel = ArmyOverviewPanel(
            self.army, self.troop_defs,
            on_close=lambda: self.army_panel.hide()
        )
        self.research_panel = ResearchPanel(
            self.research_system, self.resource_mgr,
            on_close=lambda: None,
            on_toast=lambda text, color: self.toasts.show(text, color)
        )
        self.quest_panel = QuestPanel(
            self.quest_system,
            on_close=lambda: None,
            on_toast=lambda text, color: self.toasts.show(text, color)
        )
        self.toasts = ToastManager()

        # Build button (bottom-right, opens menu)
        self._build_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 140, S.SCREEN_HEIGHT - 60, 120, 44),
            "Build", self._toggle_build_menu,
            color=S.COLOR_ACCENT
        )
        # Army button
        self._army_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 280, S.SCREEN_HEIGHT - 60, 120, 44),
            "Army", self._toggle_army_panel,
            color=S.COLOR_ACCENT2
        )
        # Heroes button
        self._heroes_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 420, S.SCREEN_HEIGHT - 60, 120, 44),
            "Heroes", lambda: self.game.state_manager.push("hero_management"),
            color=(180, 140, 220)
        )
        # World Map button
        self._map_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 560, S.SCREEN_HEIGHT - 60, 120, 44),
            "World Map", self._open_world_map,
            color=(100, 160, 220)
        )
        # Quests button
        self._quests_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 700, S.SCREEN_HEIGHT - 60, 120, 44),
            "Quests", self._toggle_quests,
            color=(220, 160, 80)
        )
        # Back to menu button
        self._menu_btn = Button(
            pygame.Rect(10, S.SCREEN_HEIGHT - 60, 100, 44),
            "Menu", self._open_pause_menu,
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
        # UI panels consume events first (overlays on top)
        if self.research_panel.handle_event(event):
            return
        if self.quest_panel.handle_event(event):
            return
        if self.training_panel.handle_event(event):
            return
        if self.army_panel.handle_event(event):
            return
        if self.info_panel.handle_event(event):
            return
        if self.build_menu.handle_event(event):
            return
        if self._build_btn.handle_event(event):
            return
        if self._army_btn.handle_event(event):
            return
        if self._heroes_btn.handle_event(event):
            return
        if self._map_btn.handle_event(event):
            return
        if self._quests_btn.handle_event(event):
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
                if self._placing or self.build_menu.visible or self.info_panel.visible:
                    self._placing = None
                    self.build_menu.hide()
                    self.info_panel.hide()
                else:
                    self._open_pause_menu()
            if event.key == pygame.K_b:
                self._toggle_build_menu()
            if event.key == pygame.K_a:
                self._toggle_army_panel()
            if event.key == pygame.K_h:
                self.game.state_manager.push("hero_management")
            if event.key == pygame.K_w:
                self._open_world_map()
            if event.key == pygame.K_q:
                self._toggle_quests()

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
                self._sm.play("build_complete")
                self._spawn_particles(b.grid_x, b.grid_y, count=20)
                # Refresh info panel if this building is selected
                if (self.info_panel.visible and
                        self.info_panel.building is b):
                    self.info_panel.show(b)

        # Training system
        trained = self.training_system.update(dt)
        for troop_id, count in trained:
            tdef = self.troop_defs.get(troop_id)
            name = tdef.name if tdef else troop_id
            self.toasts.show(f"{count}× {name} trained!", S.COLOR_ACCENT2)
            self.event_bus.emit("troops_trained",
                                troop_id=troop_id, count=count)
            self._sm.play("troop_trained")

        # Research system
        finished = self.research_system.update(dt)
        if finished:
            rdef = self.research_system.defs.get(finished)
            rname = rdef.name if rdef else finished
            self.toasts.show(f"Research complete: {rname}!", (80, 140, 220))
            self.event_bus.emit("research_complete", research_id=finished)
            self._sm.play("research_complete")
            # Apply capacity bonuses immediately
            bonuses = self.research_system.get_bonuses()
            for res, amt in bonuses.get("capacity_bonus", {}).items():
                base_cap = self.resource_mgr.get_def(res).get("base_capacity", 5000)
                self.resource_mgr.capacity[res] = base_cap + amt

        # Quest system — update army power tracking
        self.quest_system.update_army_power(
            self.army.total_power(self.troop_defs))

        # Autosave
        self.autosave_timer += dt
        if self.autosave_timer >= S.AUTOSAVE_INTERVAL:
            self.autosave_timer = 0.0
            save_game(self, "autosave")
            self.toasts.show("Auto-saved", S.COLOR_TEXT_DIM, 1.5)
            self._sm.play("save")

        # Tooltip — building hover info
        if self._hover_cell and not self._placing:
            gx, gy = self._hover_cell
            occupant = self.grid[gy][gx]
            if occupant:
                prod = occupant.production
                tip = f"{occupant.name} (Lv.{occupant.level})"
                if occupant.building:
                    tip += f"\nBuilding... {int(occupant.build_progress * 100)}%"
                elif prod:
                    parts = [f"+{v}/s {k}" for k, v in prod.items()]
                    tip += "\n" + ", ".join(parts)
                self.tooltip.set(f"building_{gx}_{gy}", tip,
                                 pygame.mouse.get_pos())
            else:
                self.tooltip.clear()
        else:
            self.tooltip.clear()
        self.tooltip.update(dt)

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
        self.army_panel.draw(surface)
        self.training_panel.draw(surface)
        self.toasts.draw(surface)
        self._build_btn.draw(surface)
        self._army_btn.draw(surface)
        self._heroes_btn.draw(surface)
        self._map_btn.draw(surface)
        self._quests_btn.draw(surface)
        self._menu_btn.draw(surface)

        # Research & quest overlays (drawn last = on top)
        self.research_panel.draw(surface)
        self.quest_panel.draw(surface)

        # Tooltip (very top)
        self.tooltip.draw(surface)

        # Quest claimable indicator on button
        claimable = self.quest_system.claimable_count
        if claimable > 0:
            badge_r = pygame.Rect(self._quests_btn.rect.right - 20,
                                  self._quests_btn.rect.y - 8, 22, 22)
            pygame.draw.circle(surface, S.COLOR_DANGER,
                               badge_r.center, 11)
            bt = render_text(str(claimable), S.FONT_SM - 4,
                             S.COLOR_WHITE, bold=True)
            surface.blit(bt, (badge_r.centerx - bt.get_width() // 2,
                              badge_r.centery - bt.get_height() // 2))

        # Research progress indicator on academy
        if self.research_system.is_researching:
            rdef = self.research_system.defs.get(self.research_system.current)
            if rdef:
                rt = render_text(
                    f"Researching: {rdef.name} ({int(self.research_system.timer)}s)",
                    S.FONT_SM - 2, (80, 140, 220))
                surface.blit(rt,
                             (S.SCREEN_WIDTH // 2 - rt.get_width() // 2,
                              S.GRID_OFFSET_Y + S.GRID_ROWS * S.TILE_SIZE + 8))

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
                self._sm.play("error")
                return None
            bt = bdef.build_time_for(1)
            b.start_build(1, bt)
        self.grid[gy][gx] = b
        self.buildings.append(b)
        self._placing = None
        self.build_menu.hide()
        if not instant:
            self.toasts.show(f"Building {bdef.name}...", S.COLOR_ACCENT)
            self._sm.play("build_start")
        return b

    def _try_place(self, gx: int, gy: int):
        if self.grid[gy][gx] is not None:
            self.toasts.show("Tile occupied!", S.COLOR_DANGER)
            self._sm.play("error")
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
            self._sm.play("error")
            return
        bt = building.definition.build_time_for(next_lvl)
        building.start_build(next_lvl, bt)
        self.toasts.show(f"Upgrading {building.name} to Lv.{next_lvl}...",
                         S.COLOR_ACCENT)
        self._sm.play("build_start")
        self.info_panel.show(building)

    def _select_building(self, building: Building):
        # If clicking barracks, open training panel instead
        if building.id == "barracks" and not building.building:
            barracks_data = building.definition.get_level_data(building.level)
            speed = barracks_data.get("training_speed", 1.0) if barracks_data else 1.0
            self.training_panel.show(building.level, speed)
            return
        # If clicking academy, open research panel
        if building.id == "academy" and not building.building:
            self.research_panel.show(building.level)
            return
        self.info_panel.show(building)
        self._selected_cell = (building.grid_x, building.grid_y)

    def _close_info(self):
        self.info_panel.hide()
        self._selected_cell = None

    def _toggle_army_panel(self):
        if self.army_panel.visible:
            self.army_panel.hide()
        else:
            self.army_panel.show()

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

    def _open_world_map(self):
        """Push the world map state with all needed context."""
        bonuses = self.research_system.get_bonuses()
        self.game.state_manager.push(
            "world_map",
            campaign=self.campaign,
            army=self.army,
            resource_mgr=self.resource_mgr,
            event_bus=self.event_bus,
            heroes=self.heroes,
            research_bonuses=bonuses
        )

    def _toggle_quests(self):
        if self.quest_panel.visible:
            self.quest_panel.hide()
        else:
            self.quest_panel.show()

    def _open_pause_menu(self):
        """Push the pause menu overlay."""
        self._sm.play("click")
        self.game.state_manager.push("pause_menu", base_view=self)
