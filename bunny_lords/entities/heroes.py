"""
Hero entities — definitions from JSON, hero instances with levels, gear, and abilities.
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "heroes.json")
EQUIP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "equipment.json")

# Equipment slot order
EQUIP_SLOTS = ["weapon", "armor", "helmet", "accessory"]
RARITY_ORDER = {"common": 0, "uncommon": 1, "rare": 2, "epic": 3, "legendary": 4}
RARITY_COLORS = {
    "common":    (180, 180, 180),
    "uncommon":  (80,  200, 80),
    "rare":      (80,  140, 255),
    "epic":      (180, 80,  255),
    "legendary": (255, 180, 50),
}


class EquipmentDef:
    """Static definition of an equipment piece."""
    def __init__(self, eid: str, raw: dict):
        self.id = eid
        self.name: str = raw["name"]
        self.slot: str = raw["slot"]
        self.rarity: str = raw["rarity"]
        self.stats: dict[str, float] = raw["stats"]
        self.color: tuple = tuple(raw["color"])
        self.description: str = raw["description"]

    @property
    def power(self) -> int:
        return sum(int(v) for v in self.stats.values())

    @property
    def rarity_color(self) -> tuple:
        return RARITY_COLORS.get(self.rarity, (180, 180, 180))


class HeroDef:
    """Static definition of a hero type."""
    def __init__(self, hid: str, raw: dict):
        self.id = hid
        self.name: str = raw["name"]
        self.title: str = raw["title"]
        self.description: str = raw["description"]
        self.role: str = raw["role"]
        self.base_stats: dict[str, float] = raw["base_stats"]
        self.growth: dict[str, float] = raw["growth"]
        self.color: tuple = tuple(raw["color"])
        self.abilities: list[dict] = raw.get("abilities", [])


class Hero:
    """A live hero instance with level, XP, equipment, and computed stats."""

    XP_PER_LEVEL = 100  # XP needed = level * XP_PER_LEVEL

    def __init__(self, definition: HeroDef, level: int = 1):
        self.definition = definition
        self.level = level
        self.xp = 0
        # Equipment: slot_name -> EquipmentDef or None
        self.equipment: dict[str, EquipmentDef | None] = {
            slot: None for slot in EQUIP_SLOTS
        }

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def title(self) -> str:
        return self.definition.title

    @property
    def role(self) -> str:
        return self.definition.role

    @property
    def color(self) -> tuple:
        return self.definition.color

    def stats_at_level(self, level: int | None = None) -> dict[str, float]:
        """Compute base stats for a given level (before equipment)."""
        lvl = level or self.level
        base = self.definition.base_stats
        growth = self.definition.growth
        return {
            k: base.get(k, 0) + growth.get(k, 0) * (lvl - 1)
            for k in base
        }

    @property
    def base_stats(self) -> dict[str, float]:
        return self.stats_at_level(self.level)

    @property
    def gear_stats(self) -> dict[str, float]:
        """Sum of all equipment bonuses."""
        totals: dict[str, float] = {}
        for eq in self.equipment.values():
            if eq:
                for k, v in eq.stats.items():
                    totals[k] = totals.get(k, 0) + v
        return totals

    @property
    def total_stats(self) -> dict[str, float]:
        """Base + equipment stats."""
        base = self.base_stats
        gear = self.gear_stats
        combined = dict(base)
        for k, v in gear.items():
            combined[k] = combined.get(k, 0) + v
        return combined

    @property
    def power(self) -> int:
        s = self.total_stats
        return int(s.get("hp", 0) + s.get("atk", 0) * 3
                   + s.get("def", 0) * 2 + s.get("speed", 0))

    @property
    def xp_to_next(self) -> int:
        return self.level * self.XP_PER_LEVEL

    @property
    def xp_progress(self) -> float:
        needed = self.xp_to_next
        return self.xp / needed if needed > 0 else 1.0

    def add_xp(self, amount: int) -> int:
        """Add XP, returns number of level-ups."""
        self.xp += amount
        levels_gained = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            levels_gained += 1
        return levels_gained

    def equip(self, item: EquipmentDef) -> EquipmentDef | None:
        """Equip an item, returns previously equipped item (or None)."""
        old = self.equipment.get(item.slot)
        self.equipment[item.slot] = item
        return old

    def unequip(self, slot: str) -> EquipmentDef | None:
        """Unequip from slot, returns the removed item."""
        old = self.equipment.get(slot)
        self.equipment[slot] = None
        return old

    def get_unlocked_abilities(self) -> list[dict]:
        """Return abilities unlocked at current level."""
        return [a for a in self.definition.abilities
                if a.get("unlock_level", 1) <= self.level]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "level": self.level,
            "xp": self.xp,
            "equipment": {
                slot: (eq.id if eq else None)
                for slot, eq in self.equipment.items()
            }
        }

    @classmethod
    def from_dict(cls, data: dict, hero_defs: dict[str, HeroDef],
                  equip_defs: dict[str, EquipmentDef]) -> "Hero":
        defn = hero_defs[data["id"]]
        h = cls(defn, data.get("level", 1))
        h.xp = data.get("xp", 0)
        for slot, eid in data.get("equipment", {}).items():
            if eid and eid in equip_defs:
                h.equipment[slot] = equip_defs[eid]
        return h


class Inventory:
    """Player's unequipped equipment inventory."""
    def __init__(self):
        self.items: list[EquipmentDef] = []

    def add(self, item: EquipmentDef):
        self.items.append(item)

    def remove(self, item: EquipmentDef) -> bool:
        if item in self.items:
            self.items.remove(item)
            return True
        return False

    def get_by_slot(self, slot: str) -> list[EquipmentDef]:
        return [i for i in self.items if i.slot == slot]

    def to_list(self) -> list[str]:
        return [i.id for i in self.items]

    def from_list(self, ids: list[str], equip_defs: dict[str, EquipmentDef]):
        self.items = [equip_defs[eid] for eid in ids if eid in equip_defs]


# ── Loaders ──────────────────────────────────────────────
_hero_defs: dict[str, HeroDef] = {}
_equip_defs: dict[str, EquipmentDef] = {}


def load_hero_defs() -> dict[str, HeroDef]:
    global _hero_defs
    if _hero_defs:
        return _hero_defs
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    _hero_defs = {hid: HeroDef(hid, data) for hid, data in raw.items()}
    return _hero_defs


def load_equip_defs() -> dict[str, EquipmentDef]:
    global _equip_defs
    if _equip_defs:
        return _equip_defs
    with open(EQUIP_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    _equip_defs = {eid: EquipmentDef(eid, data) for eid, data in raw.items()}
    return _equip_defs


def get_hero_def(hid: str) -> HeroDef | None:
    if not _hero_defs:
        load_hero_defs()
    return _hero_defs.get(hid)


def get_equip_def(eid: str) -> EquipmentDef | None:
    if not _equip_defs:
        load_equip_defs()
    return _equip_defs.get(eid)
