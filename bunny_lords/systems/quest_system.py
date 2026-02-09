"""
Quest System — tracks achievement and daily quest progress.

Listens to EventBus events and updates quest progress automatically.
"""
from __future__ import annotations
import json
import os

DATA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "quests.json")


class QuestDef:
    """Static definition of a quest."""
    def __init__(self, qid: str, raw: dict):
        self.id = qid
        self.name: str = raw["name"]
        self.description: str = raw["description"]
        self.category: str = raw["category"]          # "achievement" or "daily"
        self.track_type: str = raw["type"]             # event type to track
        self.target: int = raw["target"]
        self.rewards: dict[str, int] = raw["rewards"]
        self.repeatable: bool = raw.get("repeatable", False)


class Quest:
    """Live quest instance with progress tracking."""
    def __init__(self, definition: QuestDef):
        self.definition = definition
        self.progress: int = 0
        self.claimed: bool = False
        self.last_claim_time: float = 0  # timestamp of last claim (for dailies)

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def is_complete(self) -> bool:
        return self.progress >= self.definition.target

    @property
    def progress_pct(self) -> float:
        return min(1.0, self.progress / self.definition.target) if self.definition.target > 0 else 1.0

    def increment(self, amount: int = 1):
        self.progress = min(self.progress + amount, self.definition.target)

    def set_progress(self, value: int):
        """Set absolute progress (for things like army_power)."""
        self.progress = min(value, self.definition.target)

    def reset(self):
        """Reset for repeatable quests."""
        self.progress = 0
        self.claimed = False

    def can_claim_daily(self, current_time: float) -> bool:
        """Check if enough time has passed since last claim (24 hours)."""
        if self.definition.category != "daily":
            return True
        # 24 hours = 86400 seconds
        return (current_time - self.last_claim_time) >= 86400


class QuestSystem:
    """Manages all quests and integrates with EventBus for tracking."""

    def __init__(self, resource_mgr, event_bus):
        self.resource_mgr = resource_mgr
        self.event_bus = event_bus
        self.defs: dict[str, QuestDef] = {}
        self.quests: dict[str, Quest] = {}
        self._load()
        self._subscribe()

    def _load(self):
        with open(DATA_PATH, encoding="utf-8") as f:
            raw = json.load(f)
        self.defs = {qid: QuestDef(qid, data) for qid, data in raw.items()}
        # Create quest instances
        for qid, qdef in self.defs.items():
            self.quests[qid] = Quest(qdef)

    def _subscribe(self):
        """Subscribe to EventBus events for automatic tracking."""
        self.event_bus.subscribe("building_complete", self._on_building_complete)
        self.event_bus.subscribe("troops_trained", self._on_troops_trained)
        self.event_bus.subscribe("campaign_complete", self._on_campaign_complete)
        self.event_bus.subscribe("research_complete", self._on_research_complete)

    # ── Event Handlers ───────────────────────────────────
    def _on_building_complete(self, **kw):
        building_id = kw.get("building_id", "")
        level = kw.get("level", 1)
        for q in self._active_quests("building_complete"):
            q.increment(1)
        # Special: castle_level type
        if building_id == "castle":
            for q in self._active_quests("castle_level"):
                q.set_progress(level)

    def _on_troops_trained(self, **kw):
        count = kw.get("count", 1)
        for q in self._active_quests("troops_trained"):
            q.increment(count)

    def _on_campaign_complete(self, **kw):
        for q in self._active_quests("campaign_complete"):
            q.increment(1)

    def _on_research_complete(self, **kw):
        for q in self._active_quests("research_complete"):
            q.increment(1)

    def update_army_power(self, power: int):
        """Call periodically to update army_power quests."""
        for q in self._active_quests("army_power"):
            q.set_progress(power)

    # ── Queries ──────────────────────────────────────────
    def _active_quests(self, track_type: str) -> list[Quest]:
        """Get quests that are tracking this event type and not yet claimed."""
        return [q for q in self.quests.values()
                if q.definition.track_type == track_type
                and not q.claimed]

    def get_achievements(self) -> list[Quest]:
        return [q for q in self.quests.values()
                if q.definition.category == "achievement"]

    def get_dailies(self) -> list[Quest]:
        return [q for q in self.quests.values()
                if q.definition.category == "daily"]

    def get_claimable(self) -> list[Quest]:
        return [q for q in self.quests.values()
                if q.is_complete and not q.claimed]

    @property
    def claimable_count(self) -> int:
        return len(self.get_claimable())

    # ── Actions ──────────────────────────────────────────
    def claim(self, quest_id: str) -> bool:
        """Claim quest rewards. Returns True on success."""
        import time
        q = self.quests.get(quest_id)
        if not q or not q.is_complete or q.claimed:
            return False
        # Check if daily quest can be claimed (24h cooldown)
        current_time = time.time()
        if not q.can_claim_daily(current_time):
            return False
        # Grant rewards
        for resource, amount in q.definition.rewards.items():
            if resource == "xp":
                continue  # handled elsewhere
            self.resource_mgr.add(resource, amount)
        q.claimed = True
        q.last_claim_time = current_time
        # If repeatable (daily), reset progress for next cycle
        if q.definition.repeatable:
            q.reset()
        return True

    def to_dict(self) -> dict:
        return {
            qid: {
                "progress": q.progress,
                "claimed": q.claimed,
                "last_claim_time": q.last_claim_time
            }
            for qid, q in self.quests.items()
        }

    def from_dict(self, data: dict):
        for qid, qdata in data.items():
            if qid in self.quests:
                self.quests[qid].progress = qdata.get("progress", 0)
                self.quests[qid].claimed = qdata.get("claimed", False)
                self.quests[qid].last_claim_time = qdata.get("last_claim_time", 0)
