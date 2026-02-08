"""
Resource System — manages player resources, production ticks, capacity.
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "resources.json")


class ResourceManager:
    """Tracks the player's four resource pools + capacity."""

    def __init__(self):
        self.resources: dict[str, float] = {}
        self.capacity: dict[str, float] = {}
        self._defs: dict[str, dict] = {}
        self._load_defs()
        self._init_resources()

    def _load_defs(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            self._defs = json.load(f)

    def _init_resources(self):
        for rid, data in self._defs.items():
            self.resources[rid] = float(data["starting_amount"])
            self.capacity[rid] = float(data["base_capacity"])

    @property
    def resource_names(self) -> list[str]:
        return list(self._defs.keys())

    def get_def(self, rid: str) -> dict:
        return self._defs.get(rid, {})

    def get(self, rid: str) -> float:
        return self.resources.get(rid, 0)

    def add(self, rid: str, amount: float):
        cur = self.resources.get(rid, 0)
        cap = self.capacity.get(rid, float("inf"))
        self.resources[rid] = min(cur + amount, cap)

    def spend(self, rid: str, amount: float) -> bool:
        """Deduct. Returns True on success, False if insufficient."""
        if self.resources.get(rid, 0) >= amount:
            self.resources[rid] -= amount
            return True
        return False

    def can_afford(self, cost: dict[str, int | float]) -> bool:
        return all(self.resources.get(r, 0) >= amt
                   for r, amt in cost.items())

    def pay(self, cost: dict[str, int | float]) -> bool:
        """Deduct a full cost dict atomically. Returns False if can't afford."""
        if not self.can_afford(cost):
            return False
        for r, amt in cost.items():
            self.resources[r] -= amt
        return True

    def add_capacity(self, rid: str, bonus: float):
        self.capacity[rid] = self.capacity.get(rid, 0) + bonus

    def apply_production(self, buildings: list):
        """Called once per resource tick. Sums all building production."""
        for b in buildings:
            prod = b.production  # dict {resource_id: amount}
            for rid, amount in prod.items():
                self.add(rid, amount)

    def to_dict(self) -> dict:
        return {
            "resources": dict(self.resources),
            "capacity": dict(self.capacity),
        }

    def from_dict(self, data: dict):
        self.resources = {k: float(v) for k, v in data.get("resources", {}).items()}
        self.capacity = {k: float(v) for k, v in data.get("capacity", {}).items()}
        # Ensure all resource types exist
        for rid in self._defs:
            self.resources.setdefault(rid, 0)
            self.capacity.setdefault(rid, self._defs[rid]["base_capacity"])
