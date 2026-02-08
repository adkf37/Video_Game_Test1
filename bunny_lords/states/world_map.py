"""
World Map — scrollable campaign map with stage nodes, resource raids, and back-to-base.

Campaign stages shown as connected nodes, unlocked progressively.
Player can tap a stage to see info and start a battle.
"""
from __future__ import annotations
import pygame
import math

from core.state_machine import GameState
from systems.combat_system import CombatEngine, CampaignData
from entities.troops import load_troop_defs, Army
from entities.heroes import Hero
from utils.asset_loader import render_text
from utils.draw_helpers import (draw_rounded_panel, draw_progress_bar,
                                draw_bunny_icon)
from ui.widgets import Button
import settings as S


# ── Layout ───────────────────────────────────────────────
NODE_RADIUS = 30
NODE_SPACING_X = 110
NODE_SPACING_Y = 65
MAP_START_X = 120
MAP_START_Y = 160
PATH_COLOR = (70, 75, 100)
NODE_LOCKED = (90, 90, 100)
NODE_UNLOCKED = S.COLOR_ACCENT
NODE_CLEARED = S.COLOR_ACCENT2
NODE_SELECTED = (255, 220, 100)


class WorldMapState(GameState):
    """Scrollable world/campaign map."""

    def __init__(self, game):
        super().__init__(game)
        self.troop_defs = load_troop_defs()

        # These get set from base_view via enter()
        self.campaign: CampaignData | None = None
        self.army: Army | None = None
        self.resource_mgr = None
        self.event_bus = None
        self.heroes: list[Hero] = []
        self.research_bonuses: dict = {}

        self._selected: str | None = None
        self._scroll_x = 0
        self._hover_node: str | None = None
        self._node_positions: dict[str, tuple[int, int]] = {}

        # Buttons
        self._back_btn = Button(
            pygame.Rect(10, S.SCREEN_HEIGHT - 60, 120, 44),
            "Back", self._go_back,
            color=(80, 80, 100)
        )
        self._attack_btn = Button(
            pygame.Rect(0, 0, 160, 44),
            "Attack!", self._launch_battle,
            color=S.COLOR_DANGER
        )

    def enter(self, **params):
        """
        Expected params from base_view:
          campaign, army, resource_mgr, event_bus, heroes, research_bonuses
        """
        self.campaign = params.get("campaign")
        self.army = params.get("army")
        self.resource_mgr = params.get("resource_mgr")
        self.event_bus = params.get("event_bus")
        self.heroes = params.get("heroes", [])
        self.research_bonuses = params.get("research_bonuses", {})
        self._selected = None
        self._scroll_x = 0
        self._compute_node_positions()

    def _compute_node_positions(self):
        """Layout campaign nodes in a snaking path."""
        if not self.campaign:
            return
        self._node_positions.clear()
        stages = list(self.campaign.stages.keys())
        for i, sid in enumerate(stages):
            col = i
            # Snaking: odd rows offset down
            row_offset = 20 * math.sin(i * 0.8)
            x = MAP_START_X + col * NODE_SPACING_X
            y = MAP_START_Y + int(row_offset)
            self._node_positions[sid] = (x, y)

    def handle_event(self, event: pygame.event.Event):
        if self._back_btn.handle_event(event):
            return
        if self._selected and self._attack_btn.handle_event(event):
            return

        if event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            self._hover_node = None
            for sid, (nx, ny) in self._node_positions.items():
                sx = nx - self._scroll_x
                if math.hypot(mx - sx, my - ny) < NODE_RADIUS + 5:
                    self._hover_node = sid
                    break

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._hover_node:
                self._selected = self._hover_node

        if event.type == pygame.MOUSEWHEEL:
            self._scroll_x -= event.y * 40
            max_scroll = max(0, len(self._node_positions) * NODE_SPACING_X - S.SCREEN_WIDTH + 200)
            self._scroll_x = max(0, min(self._scroll_x, max_scroll))

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self._go_back()
            elif event.key == pygame.K_LEFT:
                self._scroll_x = max(0, self._scroll_x - 60)
            elif event.key == pygame.K_RIGHT:
                max_sc = max(0, len(self._node_positions) * NODE_SPACING_X - S.SCREEN_WIDTH + 200)
                self._scroll_x = min(max_sc, self._scroll_x + 60)

    def update(self, dt: float):
        pass  # Map is static; battle is in separate state

    def draw(self, surface: pygame.Surface):
        surface.fill((25, 30, 45))

        # Title
        title = render_text("World Map — Campaign", S.FONT_LG,
                            S.COLOR_ACCENT, bold=True)
        surface.blit(title, (S.SCREEN_WIDTH // 2 - title.get_width() // 2, 16))

        # Army power indicator
        if self.army:
            power = self.army.total_power(self.troop_defs)
            pt = render_text(f"Army Power: {power}", S.FONT_SM,
                             S.COLOR_ACCENT2, bold=True)
            surface.blit(pt, (S.SCREEN_WIDTH - pt.get_width() - 20, 22))

        troop_count_txt = render_text(
            f"Troops: {self.army.total_count if self.army else 0}",
            S.FONT_SM, S.COLOR_TEXT_DIM)
        surface.blit(troop_count_txt, (S.SCREEN_WIDTH - troop_count_txt.get_width() - 20, 44))

        # Draw path connections
        stages = list(self._node_positions.keys())
        for i in range(len(stages) - 1):
            p1 = self._node_positions[stages[i]]
            p2 = self._node_positions[stages[i + 1]]
            sx1 = p1[0] - self._scroll_x
            sx2 = p2[0] - self._scroll_x
            pygame.draw.line(surface, PATH_COLOR,
                             (sx1, p1[1]), (sx2, p2[1]), 3)

        # Draw nodes
        for sid, (nx, ny) in self._node_positions.items():
            sx = nx - self._scroll_x
            if sx < -50 or sx > S.SCREEN_WIDTH + 50:
                continue  # cull off-screen

            stage = self.campaign.stages[sid] if self.campaign else {}
            is_cleared = sid in (self.campaign.completed if self.campaign else set())
            is_unlocked = self.campaign.is_unlocked(sid) if self.campaign else False
            is_selected = sid == self._selected
            is_hover = sid == self._hover_node

            # Node color
            if is_selected:
                color = NODE_SELECTED
            elif is_cleared:
                color = NODE_CLEARED
            elif is_unlocked:
                color = NODE_UNLOCKED
            else:
                color = NODE_LOCKED

            # Glow for hover/selected
            if is_hover or is_selected:
                glow = pygame.Surface((NODE_RADIUS * 3, NODE_RADIUS * 3),
                                      pygame.SRCALPHA)
                pygame.draw.circle(glow, (*color[:3], 50),
                                   (NODE_RADIUS * 3 // 2, NODE_RADIUS * 3 // 2),
                                   NODE_RADIUS + 10)
                surface.blit(glow, (sx - NODE_RADIUS * 3 // 2,
                                    ny - NODE_RADIUS * 3 // 2))

            # Main circle
            pygame.draw.circle(surface, color, (sx, ny), NODE_RADIUS)
            pygame.draw.circle(surface, S.COLOR_WHITE, (sx, ny),
                               NODE_RADIUS, 2)

            # Stage number
            stage_num = sid.replace("stage_", "")
            num_txt = render_text(stage_num, S.FONT_MD, S.COLOR_BLACK, bold=True)
            surface.blit(num_txt, (sx - num_txt.get_width() // 2,
                                   ny - num_txt.get_height() // 2))

            # Stars (if cleared)
            if is_cleared:
                star = render_text("★", S.FONT_SM, S.COLOR_ACCENT)
                surface.blit(star, (sx - star.get_width() // 2,
                                    ny + NODE_RADIUS + 4))

            # Name below
            name = stage.get("name", sid)
            name_txt = render_text(name, S.FONT_SM - 2,
                                   S.COLOR_TEXT if is_unlocked else S.COLOR_TEXT_DIM)
            surface.blit(name_txt, (sx - name_txt.get_width() // 2,
                                    ny + NODE_RADIUS + 20))

            # Lock icon for locked stages
            if not is_unlocked and not is_cleared:
                lock = render_text("🔒", S.FONT_SM, S.COLOR_TEXT_DIM)
                surface.blit(lock, (sx - lock.get_width() // 2,
                                    ny - NODE_RADIUS - 20))

        # Selected stage info panel
        if self._selected and self.campaign:
            self._draw_stage_info(surface)

        # Back button
        self._back_btn.draw(surface)

        # Scroll hint
        hint = render_text("← → or scroll to navigate", S.FONT_SM - 2,
                           S.COLOR_TEXT_DIM)
        surface.blit(hint, (S.SCREEN_WIDTH // 2 - hint.get_width() // 2,
                            S.SCREEN_HEIGHT - 22))

    def _draw_stage_info(self, surface: pygame.Surface):
        """Draw info panel for the selected campaign stage."""
        stage = self.campaign.stages.get(self._selected, {})
        if not stage:
            return

        is_cleared = self._selected in self.campaign.completed
        is_unlocked = self.campaign.is_unlocked(self._selected)

        # Panel
        pw, ph = 380, 320
        panel_rect = pygame.Rect(S.SCREEN_WIDTH // 2 - pw // 2,
                                 S.SCREEN_HEIGHT // 2 - ph // 2 + 40,
                                 pw, ph)
        border_color = NODE_CLEARED if is_cleared else (
            S.COLOR_ACCENT if is_unlocked else NODE_LOCKED)
        draw_rounded_panel(surface, panel_rect, S.COLOR_PANEL,
                           border_color=border_color, radius=10, alpha=240)

        x, y = panel_rect.x + 16, panel_rect.y + 12

        # Stage name + difficulty
        nt = render_text(stage.get("name", ""), S.FONT_MD,
                         S.COLOR_ACCENT, bold=True)
        surface.blit(nt, (x, y))
        diff = stage.get("difficulty", 1)
        dt_txt = render_text(f"Difficulty: {'★' * diff}",
                             S.FONT_SM, S.COLOR_ACCENT)
        surface.blit(dt_txt, (x, y + 28))
        y += 54

        # Description
        desc = render_text(stage.get("description", ""), S.FONT_SM - 2,
                           S.COLOR_TEXT_DIM)
        surface.blit(desc, (x, y))
        y += 24

        # Enemy army
        enemies = stage.get("enemies", {})
        et = render_text("Enemy Forces:", S.FONT_SM, S.COLOR_DANGER, bold=True)
        surface.blit(et, (x, y))
        y += 20
        for tid, count in enemies.items():
            tdef = self.troop_defs.get(tid)
            name = tdef.name if tdef else tid
            color = S.TROOP_TYPE_COLORS.get(
                tdef.type if tdef else "infantry", S.COLOR_TEXT)
            et = render_text(f"  {count}× {name}", S.FONT_SM - 2, color)
            surface.blit(et, (x, y))
            y += 18
        y += 8

        # Recommended power
        req_power = stage.get("required_power", 0)
        player_power = self.army.total_power(self.troop_defs) if self.army else 0
        power_color = S.COLOR_ACCENT2 if player_power >= req_power else S.COLOR_DANGER
        pt = render_text(f"Rec. Power: {req_power}  (You: {player_power})",
                         S.FONT_SM, power_color)
        surface.blit(pt, (x, y))
        y += 24

        # Rewards
        rewards = stage.get("rewards", {})
        rt = render_text("Rewards:", S.FONT_SM, S.COLOR_ACCENT, bold=True)
        surface.blit(rt, (x, y))
        y += 20
        reward_parts = []
        for r, amt in rewards.items():
            reward_parts.append(f"+{amt} {r}")
        rline = render_text("  ".join(reward_parts), S.FONT_SM - 2, S.COLOR_TEXT)
        surface.blit(rline, (x, y))
        y += 24

        # Status / Attack button
        if is_cleared:
            st = render_text("★ CLEARED ★", S.FONT_SM, NODE_CLEARED, bold=True)
            surface.blit(st, (panel_rect.centerx - st.get_width() // 2, y))
            # Still allow replaying
            y += 24

        if is_unlocked or is_cleared:
            self._attack_btn.rect.topleft = (panel_rect.centerx - 80, y)
            can_attack = self.army and self.army.total_count > 0
            self._attack_btn.enabled = can_attack
            self._attack_btn.text = "Attack!" if can_attack else "No Troops!"
            self._attack_btn.draw(surface)
        else:
            lt = render_text("Complete previous stages to unlock",
                             S.FONT_SM - 2, S.COLOR_TEXT_DIM)
            surface.blit(lt, (panel_rect.centerx - lt.get_width() // 2, y))

        # Close hint
        close = render_text("Click another node or press Esc",
                            S.FONT_SM - 4, S.COLOR_TEXT_DIM)
        surface.blit(close, (panel_rect.centerx - close.get_width() // 2,
                             panel_rect.bottom - 18))

    def _launch_battle(self):
        """Start combat for the selected stage."""
        if not self._selected or not self.campaign or not self.army:
            return
        stage = self.campaign.stages.get(self._selected)
        if not stage:
            return
        if self.army.total_count <= 0:
            return

        # Build combat engine
        engine = CombatEngine(
            self.troop_defs,
            hero_list=self.heroes,
            research_bonuses=self.research_bonuses
        )

        # Resolve battle
        result = engine.resolve(
            player_army=dict(self.army.troops),
            enemy_army=stage.get("enemies", {})
        )

        # Push battle view
        self.game.state_manager.push(
            "battle_view",
            result=result,
            stage_data=stage,
            stage_id=self._selected,
            army=self.army,
            resource_mgr=self.resource_mgr,
            campaign=self.campaign,
            event_bus=self.event_bus
        )

    def _go_back(self):
        self.game.state_manager.pop()
