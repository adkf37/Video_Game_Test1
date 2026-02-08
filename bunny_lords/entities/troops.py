"""
Troop entities — definitions loaded from JSON + army composition.
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "troops.json")


class TroopDef:
    """Static definition of a troop type."""
    def __init__(self, tid: str, raw: dict):
        self.id = tid
        self.name: str = raw["name"]
        self.description: str = raw["description"]
        self.tier: int = raw["tier"]
        self.type: str = raw["type"]  # infantry, cavalry, ranged, siege
        self.stats: dict = raw["stats"]
        self.training_time: float = raw["training_time"]
        self.cost: dict[str, int] = raw["cost"]
        self.color: tuple = tuple(raw["color"])
        self.strong_vs: str = raw.get("strong_vs", "none")
        self.weak_vs: str = raw.get("weak_vs", "none")
        self.requires_barracks_level: int = raw.get("requires_barracks_level", 1)

    @property
    def power(self) -> int:
        s = self.stats
        return s.get("hp", 0) + s.get("atk", 0) * 2 + s.get("def", 0) + s.get("speed", 0)


class Army:
    """Player's army composition — maps troop_id → count."""
    def __init__(self):
        self.troops: dict[str, int] = {}

    def add(self, troop_id: str, count: int):
        self.troops[troop_id] = self.troops.get(troop_id, 0) + count

    def remove(self, troop_id: str, count: int) -> bool:
        cur = self.troops.get(troop_id, 0)
        if cur < count:
            return False
        self.troops[troop_id] = cur - count
        if self.troops[troop_id] <= 0:
            del self.troops[troop_id]
        return True

    def get_count(self, troop_id: str) -> int:
        return self.troops.get(troop_id, 0)

    @property
    def total_count(self) -> int:
        return sum(self.troops.values())

    def total_power(self, defs: dict[str, TroopDef]) -> int:
        total = 0
        for tid, count in self.troops.items():
            d = defs.get(tid)
            if d:
                total += d.power * count
        return total

    def to_dict(self) -> dict:
        return dict(self.troops)

    def from_dict(self, data: dict):
        self.troops = {k: int(v) for k, v in data.items()}


# ── Loader ───────────────────────────────────────────────
_troop_defs: dict[str, TroopDef] = {}


def load_troop_defs() -> dict[str, TroopDef]:
    global _troop_defs
    if _troop_defs:
        return _troop_defs
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    _troop_defs = {tid: TroopDef(tid, data) for tid, data in raw.items()}
    return _troop_defs


def get_troop_def(tid: str) -> TroopDef | None:
    if not _troop_defs:
        load_troop_defs()
    return _troop_defs.get(tid)
