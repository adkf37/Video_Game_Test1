"""
Save / Load System — serializes the full game state to JSON files.

Uses the to_dict / from_dict methods already present on entities and systems.
"""
from __future__ import annotations
import json
import os
import time
import tempfile
import shutil
import math
import settings as S
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from states.base_view import BaseViewState

SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saves")


def _ensure_dir():
    os.makedirs(SAVE_DIR, exist_ok=True)


def list_saves() -> list[dict]:
    """Return list of save metadata dicts sorted by timestamp (newest first)."""
    _ensure_dir()
    saves = []
    for fname in os.listdir(SAVE_DIR):
        if fname.endswith(".json"):
            path = os.path.join(SAVE_DIR, fname)
            for candidate in (path, path + ".bak"):
                try:
                    with open(candidate, encoding="utf-8") as f:
                        data = json.load(f)
                    if not isinstance(data, dict) or not isinstance(data.get("buildings"), list):
                        continue
                    timestamp = float(data.get("timestamp", 0))
                    if not math.isfinite(timestamp):
                        continue
                    saves.append({"filename": fname, "path": path, "timestamp": timestamp,
                                  "castle_level": data.get("castle_level", 1),
                                  "label": data.get("label", fname)})
                    break
                except (ValueError, OSError, AttributeError, TypeError):
                    continue
    saves.sort(key=lambda s: s["timestamp"], reverse=True)
    return saves


def save_game(state: "BaseViewState", slot_name: str = "autosave") -> str:
    """
    Serialize the full game state from a BaseViewState instance.
    Returns the path to the saved file.
    """
    _ensure_dir()

    castle = state._get_castle()
    castle_level = castle.level if castle else 1

    data = {
        "version": "2.0",
        "timestamp": time.time(),
        "label": slot_name,
        "castle_level": castle_level,

        # Resources
        "resources": state.resource_mgr.to_dict(),

        # Buildings
        "buildings": [b.to_dict() for b in state.buildings],

        # Army
        "army": state.army.to_dict(),

        # Training queue
        "training_queue": state.training_system.to_list(),

        # Heroes
        "heroes": [h.to_dict() for h in state.heroes],

        # Inventory (unequipped items)
        "inventory": state.inventory.to_list(),

        # Campaign progress
        "campaign_completed": list(state.campaign.completed),

        # Research
        "research": state.research_system.to_dict(),

        # Quests
        "quests": state.quest_system.to_dict(),
    }

    if not slot_name or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in slot_name):
        raise ValueError("Invalid save slot")
    path = os.path.join(SAVE_DIR, f"{slot_name}.json")
    fd, temporary = tempfile.mkstemp(dir=SAVE_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        if os.path.exists(path):
            shutil.copy2(path, path + ".bak")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)
    return path


def _decode(state, data):
    """Construct and validate replacement data before touching live progress."""
    from entities.buildings import Building
    from entities.heroes import Hero, Inventory
    from entities.troops import Army
    from systems.resource_system import ResourceManager
    from systems.training_system import TrainingSystem
    from systems.research_system import ResearchSystem
    from systems.quest_system import QuestSystem
    from core.event_bus import EventBus
    if not isinstance(data, dict) or not isinstance(data.get("buildings"), list):
        raise ValueError("Not a kingdom save")
    def finite_numbers(value):
        if isinstance(value, dict):
            for v in value.values():
                finite_numbers(v)
        elif isinstance(value, list):
            for v in value:
                finite_numbers(v)
        elif isinstance(value, (float, int)) and (not math.isfinite(value) or value < 0):
            raise ValueError("Invalid numeric value")
    finite_numbers(data)
    resources = ResourceManager()
    resources.from_dict(data.get("resources", {}))
    buildings, occupied, unique = [], set(), set()
    for raw in data["buildings"]:
        b = Building.from_dict(raw, state.building_defs)
        if (type(b.grid_x) is not int or type(b.grid_y) is not int or
                not 0 <= b.grid_x < S.GRID_COLS or not 0 <= b.grid_y < S.GRID_ROWS or
                (b.grid_x, b.grid_y) in occupied or
                not 0 <= b.level <= b.definition.defined_max_level or
                b._pending_level not in b.definition.levels or
                (b.definition.unique and b.id in unique)):
            raise ValueError("Invalid building")
        occupied.add((b.grid_x, b.grid_y))
        if b.definition.unique:
            unique.add(b.id)
        buildings.append(b)
    if "castle" not in unique:
        raise ValueError("Missing castle")
    army = Army()
    army.from_dict(data.get("army", {}))
    if any(t not in state.troop_defs or type(n) is not int for t,n in army.troops.items()):
        raise ValueError("Invalid army")
    training = TrainingSystem(army, resources)
    training.from_list(data.get("training_queue", []))
    hero_data = {h["id"]: h for h in data.get("heroes", [])}
    heroes = [Hero.from_dict(hero_data[hid], state.hero_defs, state.equip_defs)
              if hid in hero_data else Hero(hdef) for hid,hdef in state.hero_defs.items()]
    if any(h.level < 1 or type(h.level) is not int for h in heroes):
        raise ValueError("Invalid hero")
    inventory = Inventory()
    inventory.from_list(data.get("inventory", []), state.equip_defs)
    research = ResearchSystem(resources)
    research.from_dict(data.get("research", {}))
    if research.current and research.current not in research.defs:
        raise ValueError("Invalid research")
    quests = QuestSystem(resources, EventBus())
    quests.from_dict(data.get("quests", {}))
    campaign = set(data.get("campaign_completed", []))
    resources.refresh_economy(buildings, research.get_bonuses())
    return resources, buildings, army, training, heroes, inventory, research, quests, campaign


def load_game(state: "BaseViewState", path: str) -> bool:
    """Load atomically, falling back to the previous save if necessary. Supports v1."""
    decoded = None
    for candidate in (path, path + ".bak"):
        try:
            with open(candidate, encoding="utf-8") as f:
                decoded = _decode(state, json.load(f))
            break
        except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError):
            continue
    if decoded is None:
        return False
    resources, buildings, army, training, heroes, inventory, research, quests, campaign = decoded
    # Keep system identities used by UI panels and event subscriptions.
    state.resource_mgr.from_dict(resources.to_dict())
    state.buildings[:] = buildings
    state.grid = [[None] * S.GRID_COLS for _ in range(S.GRID_ROWS)]
    for b in buildings:
        state.grid[b.grid_y][b.grid_x] = b
    state.army.from_dict(army.to_dict())
    state.training_system.queue = training.queue
    state.heroes = heroes
    state.inventory = inventory
    state.research_system.from_dict(research.to_dict())
    state.quest_system.from_dict(quests.to_dict())
    state.campaign.completed = campaign
    state.resource_mgr.refresh_economy(buildings, research.get_bonuses())
    state._placing = state._selected_cell = state._hover_cell = None
    for panel in (state.build_menu, state.info_panel, state.army_panel,
                  state.training_panel, state.research_panel, state.quest_panel):
        panel.hide()
    state._particles.clear()
    state.toasts._toasts.clear()
    state.autosave_timer = state.resource_tick_timer = 0
    return True



def delete_save(path: str) -> bool:
    """Delete a save file."""
    try:
        os.remove(path)
        return True
    except OSError:
        return False
