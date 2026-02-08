"""
Combat System — auto-battle engine that resolves army vs army fights.

Factors in troop type advantages, hero bonuses, and research bonuses.
Produces a battle log and determines victory/defeat + rewards.
"""
from __future__ import annotations
import json
import os
import random
import math

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "campaign.json")

# Type advantage multiplier
TYPE_ADVANTAGE = {
    "infantry": "cavalry",   # infantry strong vs cavalry
    "cavalry": "ranged",     # cavalry strong vs ranged
    "ranged": "infantry",    # ranged strong vs infantry
    "siege": "siege",        # siege neutral
}


class BattleUnit:
    """A group of identical troops in combat."""
    def __init__(self, troop_id: str, name: str, troop_type: str,
                 count: int, hp: float, atk: float, defense: float,
                 speed: float, color: tuple, side: str):
        self.troop_id = troop_id
        self.name = name
        self.troop_type = troop_type
        self.count = count
        self.max_count = count
        self.hp_per_unit = hp
        self.total_hp = hp * count
        self.max_hp = self.total_hp
        self.atk = atk
        self.defense = defense
        self.speed = speed
        self.color = color
        self.side = side  # "player" or "enemy"

    @property
    def alive(self) -> bool:
        return self.total_hp > 0 and self.count > 0

    @property
    def hp_pct(self) -> float:
        return self.total_hp / self.max_hp if self.max_hp > 0 else 0

    def take_damage(self, damage: float) -> int:
        """Apply damage, returns units killed."""
        self.total_hp = max(0, self.total_hp - damage)
        new_count = max(0, math.ceil(self.total_hp / self.hp_per_unit)) if self.total_hp > 0 else 0
        killed = self.count - new_count
        self.count = new_count
        return killed


class BattleLog:
    """Records combat events for replay in battle view."""
    def __init__(self):
        self.entries: list[dict] = []

    def add(self, tick: int, event_type: str, **data):
        self.entries.append({"tick": tick, "type": event_type, **data})


class CampaignData:
    """Loaded campaign stage definitions."""
    def __init__(self):
        self.stages: dict[str, dict] = {}
        self.completed: set[str] = set()  # stages the player has beaten
        self._load()

    def _load(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            self.stages = json.load(f)

    def get_stage(self, stage_id: str) -> dict | None:
        return self.stages.get(stage_id)

    def is_unlocked(self, stage_id: str) -> bool:
        """A stage is unlocked if it has no 'requires' or the previous stage is completed."""
        stage = self.stages.get(stage_id)
        if not stage:
            return False
        req = stage.get("requires")
        if not req:
            return True
        # requires field matches the previous stage_id
        # Find which stage unlocks this one
        for sid, sdata in self.stages.items():
            if sdata.get("unlock_next") == stage_id and sid in self.completed:
                return True
        # First stage is always unlocked
        if stage_id == "stage_1":
            return True
        return False

    def complete_stage(self, stage_id: str):
        self.completed.add(stage_id)

    @property
    def total_completed(self) -> int:
        return len(self.completed)


class CombatEngine:
    """Resolves a battle between two armies."""

    MAX_TICKS = 100  # prevent infinite battles

    def __init__(self, troop_defs: dict, hero_list: list = None,
                 research_bonuses: dict = None):
        self.troop_defs = troop_defs
        self.heroes = hero_list or []
        self.research = research_bonuses or {}

    def build_player_units(self, army_dict: dict[str, int]) -> list[BattleUnit]:
        """Create BattleUnits from the player's army composition."""
        units = []
        troop_bonus = self.research.get("troop_bonus", {})
        for tid, count in army_dict.items():
            if count <= 0:
                continue
            tdef = self.troop_defs.get(tid)
            if not tdef:
                continue
            stats = tdef.stats.copy()
            # Apply research bonuses
            for stat, mult in troop_bonus.items():
                if stat in stats:
                    stats[stat] = stats[stat] * (1 + mult)
            # Apply hero bonus (average of all heroes' relevant stats)
            hero_atk_bonus = 0
            hero_def_bonus = 0
            for h in self.heroes:
                hs = h.total_stats
                hero_atk_bonus += hs.get("atk", 0) * 0.02  # 2% of hero atk per hero
                hero_def_bonus += hs.get("def", 0) * 0.02
            stats["atk"] = stats.get("atk", 0) * (1 + hero_atk_bonus)
            stats["def"] = stats.get("def", 0) * (1 + hero_def_bonus)

            units.append(BattleUnit(
                troop_id=tid,
                name=tdef.name,
                troop_type=tdef.type,
                count=count,
                hp=stats.get("hp", 50),
                atk=stats.get("atk", 10),
                defense=stats.get("def", 5),
                speed=stats.get("speed", 5),
                color=tdef.color,
                side="player"
            ))
        return units

    def build_enemy_units(self, enemy_dict: dict[str, int]) -> list[BattleUnit]:
        """Create BattleUnits for the enemy side."""
        units = []
        for tid, count in enemy_dict.items():
            if count <= 0:
                continue
            tdef = self.troop_defs.get(tid)
            if not tdef:
                continue
            stats = tdef.stats.copy()
            units.append(BattleUnit(
                troop_id=tid,
                name=tdef.name,
                troop_type=tdef.type,
                count=count,
                hp=stats.get("hp", 50),
                atk=stats.get("atk", 10),
                defense=stats.get("def", 5),
                speed=stats.get("speed", 5),
                color=tdef.color,
                side="enemy"
            ))
        return units

    def resolve(self, player_army: dict[str, int],
                enemy_army: dict[str, int]) -> dict:
        """
        Run the full auto-battle. Returns:
        {
            "victory": bool,
            "log": BattleLog,
            "player_units": [...],  # final state
            "enemy_units": [...],
            "player_losses": {troop_id: count},
            "enemy_losses": {troop_id: count},
            "ticks": int,
        }
        """
        p_units = self.build_player_units(player_army)
        e_units = self.build_enemy_units(enemy_army)

        log = BattleLog()

        # Record initial state
        log.add(0, "start",
                player=[{"id": u.troop_id, "count": u.count, "name": u.name}
                        for u in p_units],
                enemy=[{"id": u.troop_id, "count": u.count, "name": u.name}
                       for u in e_units])

        # Initial counts for loss tracking
        p_initial = {u.troop_id: u.count for u in p_units}
        e_initial = {u.troop_id: u.count for u in e_units}

        # Apply trap damage from research
        trap_dmg = self.research.get("trap_damage", 0)
        if trap_dmg > 0:
            for eu in e_units:
                dmg = eu.max_hp * trap_dmg
                eu.take_damage(dmg)
                log.add(0, "trap", target=eu.name, damage=int(dmg))

        # Sort by speed for turn order
        all_units = p_units + e_units
        all_units.sort(key=lambda u: u.speed, reverse=True)

        tick = 0
        while tick < self.MAX_TICKS:
            tick += 1
            p_alive = [u for u in p_units if u.alive]
            e_alive = [u for u in e_units if u.alive]

            if not p_alive or not e_alive:
                break

            # Each alive unit attacks once per tick
            for unit in all_units:
                if not unit.alive:
                    continue
                targets = e_alive if unit.side == "player" else p_alive
                if not targets:
                    break

                # Pick target (prefer type advantage)
                target = self._pick_target(unit, targets)

                # Calculate damage
                damage = self._calc_damage(unit, target)

                killed = target.take_damage(damage)

                log.add(tick, "attack",
                        attacker=unit.name, attacker_side=unit.side,
                        attacker_id=unit.troop_id,
                        defender=target.name, defender_side=target.side,
                        defender_id=target.troop_id,
                        damage=int(damage), killed=killed)

                # Refresh alive lists
                p_alive = [u for u in p_units if u.alive]
                e_alive = [u for u in e_units if u.alive]
                if not p_alive or not e_alive:
                    break

        # Determine outcome
        p_alive = [u for u in p_units if u.alive]
        e_alive = [u for u in e_units if u.alive]
        victory = len(p_alive) > 0 and len(e_alive) == 0

        # Calculate losses
        p_losses = {}
        for u in p_units:
            lost = p_initial[u.troop_id] - u.count
            if lost > 0:
                p_losses[u.troop_id] = lost
        e_losses = {}
        for u in e_units:
            lost = e_initial[u.troop_id] - u.count
            if lost > 0:
                e_losses[u.troop_id] = lost

        log.add(tick, "end", victory=victory)

        return {
            "victory": victory,
            "log": log,
            "player_units": p_units,
            "enemy_units": e_units,
            "player_losses": p_losses,
            "enemy_losses": e_losses,
            "ticks": tick,
        }

    def _pick_target(self, attacker: BattleUnit,
                     targets: list[BattleUnit]) -> BattleUnit:
        """Pick the best target — prefer type advantage, else lowest HP."""
        advantaged = TYPE_ADVANTAGE.get(attacker.troop_type)
        adv_targets = [t for t in targets if t.troop_type == advantaged]
        if adv_targets:
            return min(adv_targets, key=lambda t: t.total_hp)
        return min(targets, key=lambda t: t.total_hp)

    def _calc_damage(self, attacker: BattleUnit,
                     defender: BattleUnit) -> float:
        """Calculate damage with type advantage and RNG spread."""
        base_dmg = attacker.atk * attacker.count
        defense_reduction = defender.defense * 0.5
        net = max(1, base_dmg - defense_reduction)

        # Type advantage multiplier
        advantaged_type = TYPE_ADVANTAGE.get(attacker.troop_type)
        if defender.troop_type == advantaged_type:
            net *= 1.3  # 30% bonus
        elif TYPE_ADVANTAGE.get(defender.troop_type) == attacker.troop_type:
            net *= 0.75  # 25% penalty

        # Small RNG spread ±10%
        spread = random.uniform(0.9, 1.1)
        return net * spread
