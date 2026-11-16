"""
Battle View — animated auto-battle screen.

Shows player units (left) vs enemy units (right), with health bars,
floating damage numbers, particle effects, and speed controls.
"""
from __future__ import annotations
import pygame
import random
import math

from core.state_machine import GameState
from systems.combat_system import CombatEngine, BattleUnit, BattleLog
from systems.sound_manager import get_sound_manager
from utils.asset_loader import render_text, get_font
from utils.draw_helpers import draw_rounded_panel, draw_progress_bar, draw_bunny_icon
from ui.widgets import Button
import settings as S


# ── Battle-specific constants ────────────────────────────
BATTLE_AREA_Y = 100
BATTLE_AREA_H = 440
UNIT_SLOT_W = 140
UNIT_SLOT_H = 90
TICK_DURATION = 0.6  # seconds per battle tick at 1x speed


class FloatingText:
    """A damage number or status text that floats upward and fades."""
    def __init__(self, x: float, y: float, text: str, color: tuple):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.life = 1.2
        self.max_life = 1.2
        self.vy = -60  # pixels/sec upward

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float):
        self.y += self.vy * dt
        self.life -= dt

    def draw(self, surface: pygame.Surface):
        alpha = min(1.0, self.life / 0.4)
        txt = render_text(self.text, S.FONT_SM, self.color, bold=True)
        txt.set_alpha(int(255 * alpha))
        surface.blit(txt, (int(self.x) - txt.get_width() // 2, int(self.y)))


class BattleParticle:
    """Small particle for hit effects."""
    def __init__(self, x: float, y: float, color: tuple):
        self.x = x
        self.y = y
        self.vx = random.uniform(-80, 80)
        self.vy = random.uniform(-100, -20)
        self.life = random.uniform(0.3, 0.8)
        self.max_life = self.life
        self.size = random.uniform(2, 5)
        self.color = color

    @property
    def alive(self) -> bool:
        return self.life > 0

    def update(self, dt: float):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 200 * dt  # gravity
        self.life -= dt

    def draw(self, surface: pygame.Surface):
        alpha = min(1.0, self.life / 0.2)
        pygame.draw.circle(surface, self.color,
                           (int(self.x), int(self.y)),
                           max(1, int(self.size * (self.life / self.max_life))))


class BattleViewState(GameState):
    """Animated auto-battle screen that plays back combat results."""

    IS_OVERLAY = False

    def __init__(self, game):
        super().__init__(game)
        self._sm = get_sound_manager()
        self.result: dict = {}
        self.log: BattleLog | None = None
        self.stage_data: dict = {}
        self.stage_id: str = ""

        # Animation state
        self._tick_index = 0
        self._tick_timer = 0.0
        self._speed = 1.0  # 1x, 2x, or skip
        self._phase = "battle"  # "battle", "result"
        self._floats: list[FloatingText] = []
        self._particles: list[BattleParticle] = []

        # Snapshot of units for drawing (updated each tick)
        self._p_units: list[BattleUnit] = []
        self._e_units: list[BattleUnit] = []

        # Shake effect
        self._shake_timer = 0.0
        self._shake_x = 0
        self._shake_y = 0

        # Buttons
        self._speed_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 150, S.SCREEN_HEIGHT - 55, 60, 40),
            "1x", self._toggle_speed,
            color=S.COLOR_ACCENT
        )
        self._skip_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH - 80, S.SCREEN_HEIGHT - 55, 60, 40),
            "Skip", self._skip_battle,
            color=(180, 80, 80)
        )
        self._done_btn = Button(
            pygame.Rect(S.SCREEN_WIDTH // 2 - 80, S.SCREEN_HEIGHT - 70, 160, 50),
            "Continue", self._finish,
            color=S.COLOR_ACCENT2
        )

    def enter(self, **params):
        """
        Expected params:
          result: dict from CombatEngine.resolve()
          stage_data: dict from campaign
          stage_id: str
          army: Army (player's army to deduct losses from)
          resource_mgr: ResourceManager (to add rewards)
          campaign: CampaignData
          event_bus: EventBus
        """
        self.result = params.get("result", {})
        self.log = self.result.get("log")
        self.stage_data = params.get("stage_data", {})
        self.stage_id = params.get("stage_id", "")
        self._army = params.get("army")
        self._resource_mgr = params.get("resource_mgr")
        self._campaign = params.get("campaign")
        self._event_bus = params.get("event_bus")

        self._p_units = self.result.get("player_units", [])
        self._e_units = self.result.get("enemy_units", [])

        # Reset state
        self._tick_index = 0
        self._tick_timer = 0.0
        self._speed = 1.0
        self._phase = "battle"
        self._speed_btn.text = "1x"
        self._floats.clear()
        self._particles.clear()

        # Reset unit HP to max for animated playback
        for u in self._p_units:
            u.total_hp = u.max_hp
            u.count = u.max_count
        for u in self._e_units:
            u.total_hp = u.max_hp
            u.count = u.max_count

        # Pre-process log entries by tick
        self._ticks_data: dict[int, list[dict]] = {}
        if self.log:
            for entry in self.log.entries:
                t = entry["tick"]
                if t not in self._ticks_data:
                    self._ticks_data[t] = []
                self._ticks_data[t].append(entry)
        self._max_tick = self.result.get("ticks", 0)

    def handle_event(self, event: pygame.event.Event):
        if self._phase == "battle":
            self._speed_btn.handle_event(event)
            self._skip_btn.handle_event(event)
        elif self._phase == "result":
            self._done_btn.handle_event(event)

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self._phase == "battle":
                    self._skip_battle()
                else:
                    self._finish()

    def update(self, dt: float):
        # Update floating text and particles
        for f in self._floats:
            f.update(dt)
        self._floats = [f for f in self._floats if f.alive]
        for p in self._particles:
            p.update(dt)
        self._particles = [p for p in self._particles if p.alive]

        # Shake
        if self._shake_timer > 0:
            self._shake_timer -= dt
            self._shake_x = random.randint(-3, 3)
            self._shake_y = random.randint(-3, 3)
        else:
            self._shake_x = 0
            self._shake_y = 0

        if self._phase != "battle":
            return

        # Advance tick
        self._tick_timer += dt * self._speed
        if self._tick_timer >= TICK_DURATION:
            self._tick_timer -= TICK_DURATION
            self._tick_index += 1

            if self._tick_index > self._max_tick:
                self._end_battle()
                return

            # Process this tick's log entries
            entries = self._ticks_data.get(self._tick_index, [])
            for entry in entries:
                self._process_entry(entry)

    def _process_entry(self, entry: dict):
        etype = entry.get("type")
        if etype == "attack":
            # Find the defender unit to apply visual damage
            defender_id = entry.get("defender_id", "")
            defender_side = entry.get("defender_side", "")
            damage = entry.get("damage", 0)
            killed = entry.get("killed", 0)

            units = self._e_units if defender_side == "enemy" else self._p_units
            for u in units:
                if u.troop_id == defender_id and u.alive:
                    u.take_damage(damage)
                    # Floating damage number
                    fx, fy = self._unit_center(u, units)
                    color = S.COLOR_DANGER if damage > 50 else S.COLOR_ACCENT
                    self._floats.append(FloatingText(
                        fx + random.randint(-20, 20),
                        fy - 30,
                        f"-{damage}", color))
                    # Hit particles
                    for _ in range(min(killed + 3, 8)):
                        self._particles.append(BattleParticle(
                            fx + random.randint(-15, 15),
                            fy + random.randint(-10, 10),
                            u.color))
                    if killed > 0:
                        self._floats.append(FloatingText(
                            fx, fy - 50,
                            f"-{killed} killed", (255, 100, 100)))
                    self._shake_timer = 0.15
                    self._sm.play("battle_hit")
                    break
        elif etype == "trap":
            damage = entry.get("damage", 0)
            self._floats.append(FloatingText(
                S.SCREEN_WIDTH * 0.7, BATTLE_AREA_Y + 30,
                f"Trap! -{damage}", (255, 200, 50)))

    def _unit_center(self, unit: BattleUnit,
                     unit_list: list[BattleUnit]) -> tuple[int, int]:
        """Get screen position for a unit."""
        idx = 0
        for i, u in enumerate(unit_list):
            if u is unit:
                idx = i
                break
        if unit.side == "player":
            x = 80 + (idx % 2) * UNIT_SLOT_W
            y = BATTLE_AREA_Y + 60 + (idx // 2) * (UNIT_SLOT_H + 10)
        else:
            x = S.SCREEN_WIDTH - 80 - UNIT_SLOT_W - (idx % 2) * UNIT_SLOT_W
            y = BATTLE_AREA_Y + 60 + (idx // 2) * (UNIT_SLOT_H + 10)
        return x + UNIT_SLOT_W // 2, y + UNIT_SLOT_H // 2

    def _end_battle(self):
        """Transition to result phase, apply real consequences."""
        if self._phase == "result":
            return
        self._phase = "result"

        victory = self.result.get("victory", False)
        self._sm.play("victory" if victory else "defeat")

        # Apply losses to actual army
        if self._army:
            for tid, lost in self.result.get("player_losses", {}).items():
                self._army.remove(tid, lost)

        if victory:
            first_clear = not self._campaign or self.stage_id not in self._campaign.completed
            # Grant rewards
            rewards = self.stage_data.get("rewards", {})
            if self._resource_mgr:
                for r, amt in rewards.items():
                    if r != "xp":
                        self._resource_mgr.add(r, amt)
            if self._event_bus:
                self._event_bus.emit("hero_xp", amount=rewards.get("xp", 0))
            # Mark campaign stage complete
            if self._campaign:
                self._campaign.complete_stage(self.stage_id)
            if self._event_bus:
                self._event_bus.emit("campaign_complete",
                                     stage_id=self.stage_id, first_clear=first_clear)

    def _skip_battle(self):
        """Instantly finish playback."""
        if self._phase != "battle":
            return
        # Replay all remaining entries
        for t in range(self._tick_index + 1, self._max_tick + 1):
            entries = self._ticks_data.get(t, [])
            for entry in entries:
                self._process_entry(entry)
        self._end_battle()

    def _toggle_speed(self):
        if self._speed == 1.0:
            self._speed = 2.0
            self._speed_btn.text = "2x"
        elif self._speed == 2.0:
            self._speed = 4.0
            self._speed_btn.text = "4x"
        else:
            self._speed = 1.0
            self._speed_btn.text = "1x"

    def _finish(self):
        """Return to world map."""
        self.game.state_manager.pop()

    def draw(self, surface: pygame.Surface):
        surface.fill((20, 25, 40))
        ox, oy = self._shake_x, self._shake_y

        # Title bar
        stage_name = self.stage_data.get("name", "Battle")
        title = render_text(f"Battle: {stage_name}", S.FONT_LG,
                            S.COLOR_ACCENT, bold=True)
        surface.blit(title, (S.SCREEN_WIDTH // 2 - title.get_width() // 2 + ox,
                             20 + oy))

        # Divider line
        pygame.draw.line(surface, S.COLOR_GRID_LINE,
                         (S.SCREEN_WIDTH // 2 + ox, BATTLE_AREA_Y + oy),
                         (S.SCREEN_WIDTH // 2 + ox,
                          BATTLE_AREA_Y + BATTLE_AREA_H + oy), 2)

        # "VS" label
        vs = render_text("VS", S.FONT_XL, S.COLOR_DANGER, bold=True)
        surface.blit(vs, (S.SCREEN_WIDTH // 2 - vs.get_width() // 2 + ox,
                          BATTLE_AREA_Y + BATTLE_AREA_H // 2 - vs.get_height() // 2 + oy))

        # Side labels
        p_label = render_text("Your Army", S.FONT_MD, S.COLOR_ACCENT2, bold=True)
        surface.blit(p_label, (40 + ox, BATTLE_AREA_Y + 10 + oy))
        e_label = render_text("Enemy Army", S.FONT_MD, S.COLOR_DANGER, bold=True)
        surface.blit(e_label, (S.SCREEN_WIDTH - 40 - e_label.get_width() + ox,
                               BATTLE_AREA_Y + 10 + oy))

        # Draw units
        self._draw_units(surface, self._p_units, "player", ox, oy)
        self._draw_units(surface, self._e_units, "enemy", ox, oy)

        # Floating text
        for f in self._floats:
            f.draw(surface)
        # Particles
        for p in self._particles:
            p.draw(surface)

        # Bottom bar
        if self._phase == "battle":
            # Progress bar
            prog = self._tick_index / max(1, self._max_tick)
            bar_rect = pygame.Rect(40, S.SCREEN_HEIGHT - 30, S.SCREEN_WIDTH - 260, 14)
            draw_progress_bar(surface, bar_rect, prog,
                              fg_color=S.COLOR_ACCENT, bg_color=S.COLOR_PANEL)
            tick_txt = render_text(f"Tick {self._tick_index}/{self._max_tick}",
                                  S.FONT_SM - 2, S.COLOR_TEXT_DIM)
            surface.blit(tick_txt, (40, S.SCREEN_HEIGHT - 50))
            self._speed_btn.draw(surface)
            self._skip_btn.draw(surface)
        elif self._phase == "result":
            self._draw_result(surface)

    def _draw_units(self, surface: pygame.Surface, units: list[BattleUnit],
                    side: str, ox: int, oy: int):
        for i, u in enumerate(units):
            if side == "player":
                x = 40 + (i % 2) * UNIT_SLOT_W + ox
                y = BATTLE_AREA_Y + 50 + (i // 2) * (UNIT_SLOT_H + 10) + oy
            else:
                x = S.SCREEN_WIDTH - 40 - UNIT_SLOT_W - (i % 2) * UNIT_SLOT_W + ox
                y = BATTLE_AREA_Y + 50 + (i // 2) * (UNIT_SLOT_H + 10) + oy

            rect = pygame.Rect(x, y, UNIT_SLOT_W, UNIT_SLOT_H)

            # Background
            bg_alpha = 200 if u.alive else 80
            bg_color = S.COLOR_PANEL if u.alive else (60, 30, 30)
            draw_rounded_panel(surface, rect, bg_color, radius=6, alpha=bg_alpha)

            if not u.alive:
                # Dead overlay
                dead_txt = render_text("DEFEATED", S.FONT_SM - 2,
                                       S.COLOR_DANGER, bold=True)
                surface.blit(dead_txt, (rect.centerx - dead_txt.get_width() // 2,
                                        rect.centery - dead_txt.get_height() // 2))
                continue

            # Bunny icon
            icon_rect = pygame.Rect(x + 6, y + 6, 36, 36)
            draw_bunny_icon(surface, icon_rect, u.color)

            # Count badge
            count_txt = render_text(f"×{u.count}", S.FONT_SM, S.COLOR_WHITE, bold=True)
            surface.blit(count_txt, (x + 44, y + 6))

            # Name
            name_txt = render_text(u.name, S.FONT_SM - 2, S.COLOR_TEXT)
            surface.blit(name_txt, (x + 44, y + 24))

            # Type badge
            type_color = S.TROOP_TYPE_COLORS.get(u.troop_type, S.COLOR_TEXT_DIM)
            type_txt = render_text(u.troop_type[:3].upper(), S.FONT_SM - 4,
                                   type_color, bold=True)
            surface.blit(type_txt, (rect.right - type_txt.get_width() - 6, y + 6))

            # HP bar
            hp_rect = pygame.Rect(x + 6, y + UNIT_SLOT_H - 16, UNIT_SLOT_W - 12, 8)
            hp_color = S.COLOR_HP_GREEN if u.hp_pct > 0.4 else S.COLOR_HP_RED
            draw_progress_bar(surface, hp_rect, u.hp_pct,
                              fg_color=hp_color, bg_color=(40, 40, 50))

            # ATK/DEF line
            stat_txt = render_text(f"ATK:{int(u.atk)}  DEF:{int(u.defense)}",
                                   S.FONT_SM - 4, S.COLOR_TEXT_DIM)
            surface.blit(stat_txt, (x + 44, y + 42))

    def _draw_result(self, surface: pygame.Surface):
        victory = self.result.get("victory", False)
        losses = self.result.get("player_losses", {})
        rewards = self.stage_data.get("rewards", {}) if victory else {}
        rows = max(len(losses), len(rewards), 1)
        height = min(640, max(320, 190+rows*24))
        panel = pygame.Rect(S.SCREEN_WIDTH//2-330, S.SCREEN_HEIGHT//2-height//2, 660, height)
        accent = S.COLOR_ACCENT2 if victory else S.COLOR_DANGER
        draw_rounded_panel(surface, panel, S.COLOR_PANEL, border_color=accent, radius=14, alpha=255)
        title = render_text("VICTORY!" if victory else "DEFEAT", S.FONT_XL, accent, bold=True)
        surface.blit(title, title.get_rect(midtop=(panel.centerx, panel.y+20)))
        from ui.kingdom import label
        y = panel.y+94
        label(surface, "YOUR LOSSES", (panel.x+26,y), 13, S.COLOR_TEXT_DIM, True)
        label(surface, "REWARDS" if victory else "REGROUP", (panel.centerx+18,y), 13, S.COLOR_TEXT_DIM, True)
        for i, (tid, count) in enumerate(losses.items()):
            label(surface, f"-{count} {tid.replace('_',' ').title()}", (panel.x+26,y+30+i*24), 15, S.COLOR_DANGER)
        if not losses:
            label(surface, "Every bunny made it home.", (panel.x+26,y+30), 16, S.COLOR_ACCENT2)
        for i, (rid, amount) in enumerate(rewards.items()):
            label(surface, f"+{amount:,} {rid}", (panel.centerx+18,y+30+i*24), 16,
                  S.RESOURCE_COLORS.get(rid,S.COLOR_ACCENT2))
        if not victory:
            label(surface, "Train reinforcements and try again.", (panel.centerx+18,y+30), 15)
            label(surface, "Research can turn the tide.", (panel.centerx+18,y+57), 15, S.COLOR_TEXT_DIM)
        self._done_btn.rect.midbottom = (panel.centerx, panel.bottom-22)
        self._done_btn.draw(surface)
