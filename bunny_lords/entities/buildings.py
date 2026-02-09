"""
Building entities — definitions loaded from JSON + live building instances.
"""
from __future__ import annotations
import json
import os


DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "buildings.json")


class BuildingDef:
    """Static definition of a building type (loaded from JSON once)."""
    def __init__(self, bid: str, raw: dict):
        self.id = bid
        self.name: str = raw["name"]
        self.description: str = raw["description"]
        self.category: str = raw["category"]
        self.max_level: int = raw["max_level"]
        self.unique: bool = raw.get("unique", False)
        self.requires_castle: int = raw.get("requires_castle", 1)
        # levels dict: str(level) -> level data
        self.levels: dict[int, dict] = {
            int(k): v for k, v in raw["levels"].items()
        }

    def get_level_data(self, level: int) -> dict | None:
        return self.levels.get(level)

    def cost_for(self, level: int) -> dict[str, int]:
        data = self.get_level_data(level)
        return data.get("cost", {}) if data else {}

    def build_time_for(self, level: int) -> float:
        data = self.get_level_data(level)
        return data.get("build_time", 0) if data else 0

    def production_for(self, level: int) -> dict[str, float]:
        data = self.get_level_data(level)
        return data.get("production", {}) if data else {}

    @property
    def defined_max_level(self) -> int:
        """Highest level with data defined (may be < max_level for early game)."""
        return max(self.levels.keys()) if self.levels else 0


class Building:
    """A placed building instance in the player's base."""
    def __init__(self, definition: BuildingDef, grid_x: int, grid_y: int,
                 level: int = 1):
        self.definition = definition
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.level = level
        # Build / upgrade timer
        self.building = False        # True while under construction / upgrading
        self.build_timer = 0.0       # seconds remaining
        self.build_total = 0.0       # total build time for progress calc
        self._pending_level = level  # level being built towards
        
        # Stone quarry click mechanic
        self.click_timer = 0.0       # timer for stone quarries
        self.clicks_needed = 5       # clicks required every 10 seconds
        self.current_clicks = 0      # clicks accumulated this cycle

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @property
    def production(self) -> dict[str, float]:
        """Current resource production per tick (0 if under construction)."""
        if self.building:
            return {}
        prod = self.definition.production_for(self.level)
        # Stone quarries require clicking to produce
        if self.id == "stone_quarry" and "stone" in prod:
            if self.current_clicks < self.clicks_needed:
                return {}  # No production until clicked enough
        return prod

    @property
    def build_progress(self) -> float:
        if not self.building or self.build_total <= 0:
            return 1.0
        return 1.0 - (self.build_timer / self.build_total)

    def can_upgrade(self) -> bool:
        return (not self.building and
                self.level < self.definition.defined_max_level)

    def start_build(self, target_level: int, build_time: float):
        """Begin construction / upgrade."""
        self.building = True
        self._pending_level = target_level
        self.build_timer = build_time
        self.build_total = build_time

    def update(self, dt: float) -> bool:
        """Tick timer. Returns True if construction just completed."""
        # Stone quarry click timer
        if self.id == "stone_quarry" and not self.building:
            self.click_timer += dt
            if self.click_timer >= 10.0:  # Reset every 10 seconds
                self.click_timer = 0.0
                self.current_clicks = 0
        
        if not self.building:
            return False
        self.build_timer -= dt
        if self.build_timer <= 0:
            self.build_timer = 0.0
            self.building = False
            self.level = self._pending_level
            return True  # just completed!
        return False

    def to_dict(self) -> dict:
        """Serialize for save files."""
        return {
            "id": self.id,
            "grid_x": self.grid_x,
            "grid_y": self.grid_y,
            "level": self.level,
            "building": self.building,
            "build_timer": self.build_timer,
            "build_total": self.build_total,
            "_pending_level": self._pending_level,
            "click_timer": self.click_timer,
            "current_clicks": self.current_clicks,
        }

    @classmethod
    def from_dict(cls, data: dict, defs: dict[str, BuildingDef]) -> "Building":
        defn = defs[data["id"]]
        b = cls(defn, data["grid_x"], data["grid_y"], data["level"])
        b.building = data.get("building", False)
        b.build_timer = data.get("build_timer", 0)
        b.build_total = data.get("build_total", 0)
        b._pending_level = data.get("_pending_level", b.level)
        b.click_timer = data.get("click_timer", 0)
        b.current_clicks = data.get("current_clicks", 0)
        return b


# ── Loader ───────────────────────────────────────────────
_building_defs: dict[str, BuildingDef] = {}


def load_building_defs() -> dict[str, BuildingDef]:
    global _building_defs
    if _building_defs:
        return _building_defs
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)
    _building_defs = {bid: BuildingDef(bid, data) for bid, data in raw.items()}
    return _building_defs


def get_building_def(bid: str) -> BuildingDef | None:
    if not _building_defs:
        load_building_defs()
    return _building_defs.get(bid)
