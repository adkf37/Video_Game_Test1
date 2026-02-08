"""
Training System — manages troop training queues.

Each barracks building can have a training queue. Troops take time and resources.
"""
from __future__ import annotations
from entities.troops import TroopDef, Army, load_troop_defs
from systems.resource_system import ResourceManager


class TrainingJob:
    """A single entry in the training queue."""
    def __init__(self, troop_def: TroopDef, count: int, time_per_unit: float,
                 speed_mult: float = 1.0):
        self.troop_def = troop_def
        self.total_count = count
        self.trained_count = 0
        self.time_per_unit = time_per_unit / speed_mult
        self.timer = self.time_per_unit  # countdown for next unit

    @property
    def remaining(self) -> int:
        return self.total_count - self.trained_count

    @property
    def is_complete(self) -> bool:
        return self.trained_count >= self.total_count

    @property
    def progress(self) -> float:
        if self.total_count <= 0:
            return 1.0
        # progress within current unit + completed units
        unit_progress = 1.0 - (self.timer / self.time_per_unit) if self.time_per_unit > 0 else 1.0
        return (self.trained_count + unit_progress) / self.total_count

    def to_dict(self) -> dict:
        return {
            "troop_id": self.troop_def.id,
            "total_count": self.total_count,
            "trained_count": self.trained_count,
            "timer": self.timer,
            "time_per_unit": self.time_per_unit,
        }


class TrainingSystem:
    """Manages training queues and produces troops into the player's army."""

    MAX_QUEUE_SIZE = 5  # max concurrent training jobs

    def __init__(self, army: Army, resource_mgr: ResourceManager):
        self.army = army
        self.resource_mgr = resource_mgr
        self.troop_defs = load_troop_defs()
        self.queue: list[TrainingJob] = []

    def can_train(self, troop_id: str, count: int = 1) -> tuple[bool, str]:
        """Check if training is possible. Returns (ok, reason)."""
        tdef = self.troop_defs.get(troop_id)
        if not tdef:
            return False, "Unknown troop type"
        if len(self.queue) >= self.MAX_QUEUE_SIZE:
            return False, "Training queue full"
        total_cost = {r: amt * count for r, amt in tdef.cost.items()}
        if not self.resource_mgr.can_afford(total_cost):
            return False, "Not enough resources"
        return True, ""

    def start_training(self, troop_id: str, count: int = 1,
                       speed_mult: float = 1.0) -> bool:
        """Start training troops. Deducts resources immediately."""
        ok, reason = self.can_train(troop_id, count)
        if not ok:
            return False
        tdef = self.troop_defs[troop_id]
        total_cost = {r: amt * count for r, amt in tdef.cost.items()}
        if not self.resource_mgr.pay(total_cost):
            return False
        job = TrainingJob(tdef, count, tdef.training_time, speed_mult)
        self.queue.append(job)
        return True

    def cancel_job(self, index: int) -> bool:
        """Cancel a queued job, refund remaining resources."""
        if 0 <= index < len(self.queue):
            job = self.queue[index]
            # Refund for untrained units
            remaining = job.remaining
            if remaining > 0:
                for r, amt in job.troop_def.cost.items():
                    self.resource_mgr.add(r, amt * remaining)
            self.queue.pop(index)
            return True
        return False

    def update(self, dt: float) -> list[tuple[str, int]]:
        """Tick training. Returns list of (troop_id, count) completed this frame."""
        completed: list[tuple[str, int]] = []
        if not self.queue:
            return completed

        # Only the first job in queue actively trains
        job = self.queue[0]
        job.timer -= dt
        while job.timer <= 0 and not job.is_complete:
            job.trained_count += 1
            self.army.add(job.troop_def.id, 1)
            if not job.is_complete:
                job.timer += job.time_per_unit
            else:
                job.timer = 0

        if job.is_complete:
            completed.append((job.troop_def.id, job.total_count))
            self.queue.pop(0)

        return completed

    def get_barracks_speed(self, buildings: list) -> float:
        """Get training speed multiplier from barracks level."""
        for b in buildings:
            if b.id == "barracks" and not b.building:
                data = b.definition.get_level_data(b.level)
                if data:
                    return data.get("training_speed", 1.0)
        return 1.0

    @property
    def is_training(self) -> bool:
        return len(self.queue) > 0

    def to_list(self) -> list[dict]:
        return [j.to_dict() for j in self.queue]

    def from_list(self, data: list):
        self.queue.clear()
        for item in data:
            tdef = self.troop_defs.get(item["troop_id"])
            if tdef:
                job = TrainingJob(tdef, item["total_count"],
                                  item["time_per_unit"])
                job.trained_count = item.get("trained_count", 0)
                job.timer = item.get("timer", job.time_per_unit)
                self.queue.append(job)
