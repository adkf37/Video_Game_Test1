# Bunny Lords - Customization Guide

Welcome to **Bunny Lords**! This guide shows you where to adjust game logic, balance, and content to customize your experience.

---

## 📂 Quick Reference: Where to Find Things

### Game Data Files (JSON)
All major game content is stored in `data/` as JSON files:

| File | What It Controls |
|------|-----------------|
| `data/buildings.json` | Buildings: costs, build times, production rates, castle unlocks |
| `data/heroes.json` | Heroes: base stats, growth rates, special abilities |
| `data/quests.json` | Quests: achievement & daily quest targets, rewards |
| `data/troops.json` | Troops: stats, training costs, training times |
| `data/research_tree.json` | Research: tech tree unlocks, bonuses, requirements |
| `data/campaign.json` | Campaign stages: enemy armies, rewards, difficulty |

### Code Files (Python)
Game logic and systems are in Python modules:

| File | What It Controls |
|------|-----------------|
| `entities/buildings.py` | Building behavior, production logic, click mechanics |
| `entities/heroes.py` | Hero leveling (XP_PER_LEVEL), power calculation |
| `systems/quest_system.py` | Quest tracking, daily quest cooldowns (86400s) |
| `systems/combat_system.py` | Battle resolution, damage formulas, troop AI |
| `systems/research_system.py` | Research unlocking, bonus application |
| `settings.py` | UI colors, screen size, font sizes, game constants |

---

## 🏰 Buildings Customization

**File:** `data/buildings.json`

### Structure Example
```json
{
  "farm": {
    "name": "Farm",
    "base_cost": {"gold": 100},
    "build_time": 10,
    "max_level": 10,
    "production": {"food": 20},
    "scale_factor": 1.4
  }
}
```

### Key Fields
- **`base_cost`**: Initial build cost (gold, wood, stone, food)
- **`build_time`**: Seconds to build at level 1
- **`max_level`**: Maximum upgrade level
- **`production`**: Resources produced per second (for resource buildings)
- **`scale_factor`**: Cost multiplier per level (1.4 = 40% increase)

### Castle Level Unlocks
The `castle` building has an `"unlocks"` field per level:
```json
"castle": {
  "level_bonuses": {
    "1": { "unlocks": ["carrot_farm", "lumber_burrow"] },
    "2": { "unlocks": ["stone_quarry"] },
    "3": { "unlocks": ["barracks"], "description": "Unlock Troop Training!" },
    "4": { "unlocks": ["gold_mine", "warehouse"] },
    "5": { "unlocks": ["academy", "wall"] }
  }
}
```

**💡 Tip:** To change when troops unlock, edit the `"3"` level entry.

### Resource Building Click Bonus
**Code:** `entities/buildings.py` (lines 60-75)

Resource buildings give bonus rewards when clicked:
```python
self.click_timer = 0.0       # timer for resource buildings
self.click_available = False # whether a bonus click is available
```

Every 10 seconds, clickable resource buildings give:
- **Carrot Farm**: +15 carrots
- **Lumber Burrow**: +15 wood
- **Stone Quarry**: +15 stone
- **Gold Mine**: +15 gold

**To adjust:** Change the bonus amount in `states/base_view.py` (line 260) or the timer interval in `entities/buildings.py` (line 119).

---

## 🦸 Heroes Customization

**File:** `data/heroes.json`

### Structure Example
```json
{
  "knight": {
    "name": "Brave Knight",
    "description": "Tanky frontline fighter",
    "stats": {
      "attack": 40,
      "defense": 60,
      "hp": 200,
      "leadership": 50
    },
    "growth": {
      "attack": 3,
      "defense": 5,
      "hp": 15,
      "leadership": 4
    },
    "unlock_cost": {"gold": 5000}
  }
}
```

### Key Fields
- **`stats`**: Base stats at level 1
- **`growth`**: Stat increase per level
- **`unlock_cost`**: One-time cost to recruit hero
- **`description`**: Flavor text shown in UI

### Hero Leveling Logic
**Code:** `entities/heroes.py` (lines 20-35)

```python
XP_PER_LEVEL = 100  # XP needed to level up (constant for now)

def gain_xp(self, amount: int):
    self.xp += amount
    while self.xp >= XP_PER_LEVEL:
        self.xp -= XP_PER_LEVEL
        self.level_up()
```

**Power Calculation** (used for roster sort):
```python
def power(self) -> int:
    return int(self.stats["attack"] * 1.5 + 
               self.stats["defense"] * 1.2 + 
               self.stats["hp"] * 0.3 + 
               self.stats["leadership"] * 2)
```

**To adjust:** Change `XP_PER_LEVEL` for faster/slower leveling, or modify power weights.

### Adding Custom Hero Portraits
Hero portraits are drawn procedurally in `states/hero_management.py`:
```python
draw_bunny_icon(surface, rect, color=avg_color, eyes='normal')
```

**To use custom images:**
1. Create PNG files: `assets/sprites/heroes/knight.png`, etc.
2. Modify `hero_management.py` (line ~180) to load images:
   ```python
   hero_img = pygame.image.load(f"assets/sprites/heroes/{hero.id}.png")
   surface.blit(hero_img, rect)
   ```

---

## 🎯 Quests Customization

**File:** `data/quests.json`

### Structure Example
```json
{
  "quest_castle_5": {
    "title": "Mighty Fortress",
    "description": "Upgrade your Castle to level 5",
    "type": "building_level",
    "target": {"building": "castle", "level": 5},
    "rewards": {"gold": 2000, "xp": 150},
    "repeatable": false
  }
}
```

### Quest Types
- **`building_level`**: Requires building at specific level
  - Target: `{"building": "castle", "level": 5}`
- **`resource_collect`**: Gather X amount of resource
  - Target: `{"resource": "gold", "amount": 10000}`
- **`train_troops`**: Train X troops of any type
  - Target: `{"amount": 50}`
- **`battle_win`**: Win X campaign stages
  - Target: `{"amount": 3}`

### Daily Quest Cooldown
**Code:** `systems/quest_system.py` (lines 30-50)

Daily quests enforce a 24-hour cooldown:
```python
def can_claim_daily(self, current_time: float) -> bool:
    if not self.repeatable:
        return self.completed and not self.claimed
    # Repeatable daily quests: 24-hour cooldown
    return (self.completed and not self.claimed and 
            current_time - self.last_claim_time >= 86400)  # 24 hours in seconds
```

**To adjust:** Change `86400` to a different interval (e.g., `3600` = 1 hour).

---

## 🪖 Troops Customization

**File:** `data/troops.json`

### Structure Example
```json
{
  "infantry": {
    "name": "Infantry",
    "stats": {
      "attack": 15,
      "defense": 12,
      "hp": 50,
      "speed": 5
    },
    "cost": {"food": 20, "gold": 10},
    "train_time": 30,
    "description": "Basic melee unit"
  }
}
```

### Key Fields
- **`stats`**: Combat stats (attack, defense, hp, speed)
- **`cost`**: Resources per unit
- **`train_time`**: Seconds to train one unit
- **`description`**: Tooltip text

### Barracks Unlock
Troops require the **Barracks** building, which unlocks at **Castle Level 3** (see Buildings section).

---

## 🔬 Research Customization

**File:** `data/research_tree.json`

### Structure Example
```json
{
  "eco_1": {
    "name": "Improved Farming",
    "description": "Food production +20%",
    "cost": {"gold": 500},
    "time": 120,
    "effects": {"food_production": 1.2},
    "prereqs": []
  }
}
```

### Key Fields
- **`effects`**: Bonuses applied when researched
  - `"food_production": 1.2` = 20% increase
  - `"troop_attack": 1.1` = 10% attack boost
- **`prereqs`**: List of required research IDs before unlocking
- **`cost`** & **`time`**: Research costs and duration

---

## ⚔️ Campaign Customization

**File:** `data/campaign.json`

### Structure Example
```json
{
  "stage_1": {
    "name": "Goblin Outpost",
    "description": "Clear out the goblin raiders",
    "enemies": {
      "infantry": 10,
      "archer": 5
    },
    "rewards": {
      "gold": 500,
      "food": 300,
      "xp": 50
    },
    "required": []
  }
}
```

### Key Fields
- **`enemies`**: Troop type → count dictionary
- **`rewards`**: Resources + XP granted on victory
- **`required`**: List of stage IDs that must be completed first

### Combat Formula
**Code:** `systems/combat_system.py` (lines 100-150)

Damage calculation:
```python
def _calculate_damage(attacker_stats, defender_stats):
    base_dmg = attacker_stats["attack"]
    mitigated = base_dmg * (defender_stats["defense"] / (defender_stats["defense"] + 100))
    damage = base_dmg - mitigated
    return max(1, int(damage))  # Minimum 1 damage
```

**To adjust:** Modify the defense formula or add critical hits, armor penetration, etc.

---

## 🎨 UI & Visual Settings

**File:** `settings.py`

### Key Constants
```python
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
FPS = 60

# Colors
COLOR_BG = (20, 24, 40)
COLOR_ACCENT = (100, 180, 255)
COLOR_DANGER = (220, 80, 80)

# Fonts
FONT_XL = 32
FONT_LG = 20
FONT_MD = 16
FONT_SM = 14

# Game Balance
BASE_SAVE_INTERVAL = 60  # Auto-save every 60 seconds
```

### Building Colors
```python
BUILDING_COLORS = {
    "castle": (180, 160, 100),
    "farm": (120, 180, 60),
    "lumber_mill": (140, 100, 60),
    # ... add more
}
```

---

## 🔊 Sound Effects

**Code:** `utils/sound_manager.py`

Sounds are generated procedurally. To adjust frequencies/durations:
```python
def generate_click_sound(self):
    # Adjust frequency (Hz) and duration (ms)
    return self._sine_wave(800, 50)  # 800 Hz, 50ms
```

**Available sounds:**
- `click`, `complete`, `upgrade`, `error`, `victory`, `defeat`, `collect`, `train`, `battle_hit`, `purchase`, `quest_complete`, `menu_open`, `menu_close`, `button_hover`

---

## 🎮 Victory Animation

**Code:** `states/victory_animation.py`

Triggered after building upgrades or campaign victories. Displays a dancing bunny with confetti for 2.5 seconds.

**To adjust animation:**
```python
ANIMATION_DURATION = 2.5  # Change duration (seconds)

# In render() method:
rotation_angle += 2  # Rotation speed
bounce_offset = math.sin(t * 5) * 20  # Bounce intensity
```

---

## 🛠️ Common Modifications

### Make the game easier:
1. **Lower building costs:** Edit `base_cost` in `buildings.json`
2. **Faster build times:** Reduce `build_time` values
3. **More quest rewards:** Increase `rewards` in `quests.json`
4. **Weaker enemies:** Reduce troop counts in `campaign.json`

### Make the game harder:
1. **Higher costs:** Increase `base_cost` and `scale_factor`
2. **Longer build times:** Increase `build_time` values
3. **Tougher enemies:** Add more troops or stronger types in `campaign.json`
4. **Slower resource production:** Reduce `production` rates in `buildings.json`

### Add a new building:
1. Add entry to `data/buildings.json` with all required fields
2. Add color to `BUILDING_COLORS` in `settings.py`
3. Optionally add to castle unlock tree
4. Building appears automatically in build menu!

### Add a new hero:
1. Add entry to `data/heroes.json` with stats, growth, cost
2. Create custom portrait (see Heroes section) or use procedural bunny
3. Hero appears in recruitment panel automatically!

### Add a new quest:
1. Add entry to `data/quests.json` with type, target, rewards
2. Set `"repeatable": true` for daily quests (24-hour cooldown)
3. Quest appears in quest panel automatically!

---

## 📦 File Structure Overview

```
bunny_lords/
├── main.py                    # Game entry point
├── settings.py                # Global constants, colors, UI config
├── README.md                  # This file!
│
├── assets/
│   └── sprites/               # (future) Custom images go here
│
├── core/
│   ├── game.py                # Main game loop, state manager
│   └── state_machine.py       # State management system
│
├── data/                      # ⭐ JSON files for game content
│   ├── buildings.json
│   ├── heroes.json
│   ├── quests.json
│   ├── troops.json
│   ├── research_tree.json
│   └── campaign.json
│
├── entities/                  # Game object classes
│   ├── buildings.py           # Building logic, click mechanics
│   ├── heroes.py              # Hero XP, stats, leveling
│   └── troops.py              # Army management
│
├── systems/                   # Game systems
│   ├── quest_system.py        # Quest tracking, daily cooldowns
│   ├── combat_system.py       # Battle resolution
│   ├── research_system.py     # Tech tree
│   └── resource_manager.py    # Resource storage/production
│
├── states/                    # Game screens
│   ├── main_menu.py
│   ├── base_view.py           # Main city building screen
│   ├── hero_management.py     # Hero roster
│   ├── world_map.py           # Campaign map
│   ├── battle_view.py         # Combat playback
│   ├── help_screen.py         # Instructions overlay
│   └── victory_animation.py   # Celebration overlay
│
├── ui/
│   └── widgets.py             # Buttons, panels
│
└── utils/
    ├── asset_loader.py        # Font rendering
    ├── draw_helpers.py        # Shape drawing (bunnies!)
    └── sound_manager.py       # Procedural audio
```

---

## 🐰 Tips & Tricks

- **Test changes:** Run `python main.py` to see your edits in action
- **Start fresh:** Delete `saves/game_save.json` to reset progress
- **JSON syntax:** Use a JSON validator if you get loading errors
- **Backup files:** Copy JSON files before major changes
- **Experiment:** Most values are safe to change without breaking the game!

---

## 🚀 Running the Game

1. **Install Python 3.11+**
2. **Install pygame-ce:**
   ```bash
   pip install pygame-ce
   ```
3. **Run:**
   ```bash
   python main.py
   ```

---

## 🎉 Have Fun!

This is your game now—customize it, break it, rebuild it, and make it your own! If you add cool features, share them with others!

**Happy bunny building! 🐰**
