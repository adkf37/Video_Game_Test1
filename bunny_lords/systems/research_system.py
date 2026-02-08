"""
Research System — manages technology research tied to the Academy building.

Research provides permanent bonuses to production, combat, heroes, etc.
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "research_tree.json")


class ResearchDef:
    """Static definition of a research node."""
    def __init__(self, rid: str, raw: dict):
        self.id = rid
        self.name: str = raw["name"]
        self.category: str = raw["category"]
        self.description: str = raw["description"]
        self.effect: dict = raw["effect"]
        self.cost: dict[str, int] = raw["cost"]
        self.time: float = raw["time"]
        self.requires: list[str] = raw.get("requires", [])
        self.requires_academy: int = raw.get("requires_academy", 1)


class ResearchSystem:
    """Manages the research tree, queue, and accumulated bonuses."""

    def __init__(self, resource_mgr):
        self.resource_mgr = resource_mgr
        self.defs: dict[str, ResearchDef] = {}
        self.completed: set[str] = set()
        self.current: str | None = None      # currently researching ID
        self.timer: float = 0.0              # remaining seconds
        self.total_time: float = 0.0         # total research time
        self._load()

    def _load(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        self.defs = {rid: ResearchDef(rid, data) for rid, data in raw.items()}

    # ── Queries ──────────────────────────────────────────
    def is_researched(self, rid: str) -> bool:
        return rid in self.completed

    def is_available(self, rid: str, academy_level: int) -> bool:
        """Check if a research is unlockable (prereqs done, academy high enough)."""
        rdef = self.defs.get(rid)
        if not rdef:
            return False
        if rid in self.completed:
            return False
        if rdef.requires_academy > academy_level:
            return False
        for req in rdef.requires:
            if req not in self.completed:
                return False
        return True

    def can_afford(self, rid: str) -> bool:
        rdef = self.defs.get(rid)
        if not rdef:
            return False
        return self.resource_mgr.can_afford(rdef.cost)

    def get_by_category(self, category: str) -> list[ResearchDef]:
        return [d for d in self.defs.values() if d.category == category]

    @property
    def categories(self) -> list[str]:
        cats = []
        seen = set()
        for d in self.defs.values():
            if d.category not in seen:
                cats.append(d.category)
                seen.add(d.category)
        return cats

    @property
    def is_researching(self) -> bool:
        return self.current is not None

    @property
    def progress(self) -> float:
        if not self.current or self.total_time <= 0:
            return 0
        return 1.0 - (self.timer / self.total_time)

    @property
    def total_completed(self) -> int:
        return len(self.completed)

    # ── Actions ──────────────────────────────────────────
    def start_research(self, rid: str, academy_level: int) -> tuple[bool, str]:
        """Begin researching. Returns (success, reason)."""
        if self.is_researching:
            return False, "Already researching"
        if not self.is_available(rid, academy_level):
            return False, "Requirements not met"
        rdef = self.defs[rid]
        if not self.resource_mgr.pay(rdef.cost):
            return False, "Not enough resources"
        self.current = rid
        self.timer = rdef.time
        self.total_time = rdef.time
        return True, ""

    def cancel_research(self) -> bool:
        """Cancel current research, refund 50%."""
        if not self.current:
            return False
        rdef = self.defs[self.current]
        for r, amt in rdef.cost.items():
            self.resource_mgr.add(r, amt * 0.5)
        self.current = None
        self.timer = 0
        self.total_time = 0
        return True

    def update(self, dt: float) -> str | None:
        """Tick research timer. Returns research ID if completed this frame."""
        if not self.current:
            return None
        self.timer -= dt
        if self.timer <= 0:
            completed_id = self.current
            self.completed.add(completed_id)
            self.current = None
            self.timer = 0
            self.total_time = 0
            return completed_id
        return None

    # ── Bonus Aggregation ────────────────────────────────
    def get_bonuses(self) -> dict:
        """Aggregate all research bonuses into a single dict."""
        bonuses = {
            "production_bonus": {},   # resource_id -> multiplier
            "capacity_bonus": {},     # resource_id -> flat bonus
            "troop_bonus": {},        # stat -> multiplier
            "training_speed_bonus": 0.0,
            "defense_bonus": 0.0,
            "trap_damage": 0.0,
            "hero_xp_bonus": 0.0,
            "hero_stat_bonus": 0.0,
        }
        for rid in self.completed:
            rdef = self.defs.get(rid)
            if not rdef:
                continue
            effect = rdef.effect
            for key, val in effect.items():
                if key == "production_bonus" and isinstance(val, dict):
                    for res, mult in val.items():
                        bonuses["production_bonus"][res] = (
                            bonuses["production_bonus"].get(res, 0) + mult)
                elif key == "capacity_bonus" and isinstance(val, dict):
                    for res, amt in val.items():
                        bonuses["capacity_bonus"][res] = (
                            bonuses["capacity_bonus"].get(res, 0) + amt)
                elif key == "troop_bonus" and isinstance(val, dict):
                    for stat, mult in val.items():
                        bonuses["troop_bonus"][stat] = (
                            bonuses["troop_bonus"].get(stat, 0) + mult)
                elif key in bonuses and isinstance(bonuses[key], float):
                    bonuses[key] += val
        return bonuses

    def to_dict(self) -> dict:
        return {
            "completed": list(self.completed),
            "current": self.current,
            "timer": self.timer,
            "total_time": self.total_time,
        }

    def from_dict(self, data: dict):
        self.completed = set(data.get("completed", []))
        self.current = data.get("current")
        self.timer = data.get("timer", 0)
        self.total_time = data.get("total_time", 0)
