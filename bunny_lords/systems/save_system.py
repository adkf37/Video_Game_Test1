"""
Save / Load System — serializes the full game state to JSON files.

Uses the to_dict / from_dict methods already present on entities and systems.
"""
from __future__ import annotations
import json
import os
import time
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
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                saves.append({
                    "filename": fname,
                    "path": path,
                    "timestamp": data.get("timestamp", 0),
                    "castle_level": data.get("castle_level", 1),
                    "label": data.get("label", fname),
                })
            except (json.JSONDecodeError, OSError):
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
        "version": "1.0",
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

    filename = f"{slot_name}.json"
    path = os.path.join(SAVE_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path


def load_game(state: "BaseViewState", path: str) -> bool:
    """
    Deserialize game state into a BaseViewState instance.
    Returns True on success, False on failure.
    """
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return False

    # ── Resources ────────────────────────────────────
    state.resource_mgr.from_dict(data.get("resources", {}))

    # ── Buildings ────────────────────────────────────
    from entities.buildings import Building
    state.buildings.clear()
    state.grid = [[None] * 8 for _ in range(8)]
    for bdata in data.get("buildings", []):
        try:
            b = Building.from_dict(bdata, state.building_defs)
            state.grid[b.grid_y][b.grid_x] = b
            state.buildings.append(b)
        except (KeyError, IndexError):
            continue

    # ── Army ─────────────────────────────────────────
    state.army.from_dict(data.get("army", {}))

    # ── Training queue ───────────────────────────────
    state.training_system.from_list(data.get("training_queue", []))

    # ── Heroes ───────────────────────────────────────
    from entities.heroes import Hero
    heroes_data = data.get("heroes", [])
    for hdata in heroes_data:
        hid = hdata.get("id")
        # Find matching hero in state and update in place
        for hero in state.heroes:
            if hero.id == hid:
                hero.level = hdata.get("level", 1)
                hero.xp = hdata.get("xp", 0)
                for slot, eid in hdata.get("equipment", {}).items():
                    if eid and eid in state.equip_defs:
                        hero.equipment[slot] = state.equip_defs[eid]
                    else:
                        hero.equipment[slot] = None
                break

    # ── Inventory ────────────────────────────────────
    state.inventory.from_list(data.get("inventory", []), state.equip_defs)

    # ── Campaign ─────────────────────────────────────
    state.campaign.completed = set(data.get("campaign_completed", []))

    # ── Research ─────────────────────────────────────
    state.research_system.from_dict(data.get("research", {}))

    # ── Quests ───────────────────────────────────────
    state.quest_system.from_dict(data.get("quests", {}))

    return True


def delete_save(path: str) -> bool:
    """Delete a save file."""
    try:
        os.remove(path)
        return True
    except OSError:
        return False
