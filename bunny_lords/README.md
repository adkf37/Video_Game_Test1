# Bunny Lords — Woodland Update

A desktop strategy game about building a rabbit kingdom, raising an army, and conquering a ten-stage campaign. Built with Python and Pygame CE; illustrations and sounds are generated locally.

## Play

Requires Python 3.11 or newer. From this repository's root:

```powershell
python -m pip install -r bunny_lords/requirements.txt
python bunny_lords/main.py
```

On Windows, you can also double-click `bunny_lords/Play_Bunny_Lords.cmd` after installing the requirements. Use Continue to resume your most recent valid save.

## What's new in v2.0

- Woodland title screen, illustrated buildings, textured village plots, and a consistent green-and-gold interface.
- Kingdom dashboard with a contextual next objective, castle/army/campaign statistics, and active construction, training, and research progress.
- Resource HUD with production per second, capacity bars, and full-storage indicators.
- Collect all harvests with one click or C. Harvest rewards scale with building level, and a full warehouse no longer wastes a ready bonus.
- Building completion uses notifications and particles without interrupting play.
- Gold Mines and Warehouses unlock at Castle level 2, alongside Stone Quarries, so you can establish all four production streams early.
- Warehouse capacities stack correctly and retain their existing capacity during upgrades. Production and capacity research now apply to the economy.
- Training research affects new orders; Academy upgrades accelerate research. Queued training carries remaining elapsed time into the next order and reports each trained unit to quests.
- Battle and quest XP reaches heroes, including the research XP bonus. Hero stat research contributes to combat bonuses.
- Campaign map has a landscape, wider stage spacing, automatic selection of the next stage, and larger stage details. Locked stages cannot be attacked. Replay victories still grant loot but do not inflate unique-stage achievements.
- Daily quests repeat with a 24-hour claim cooldown and show the remaining cooldown. Old claimed daily quests become available again when their cooldown expires.
- Construction, research, training, and production continue while viewing Heroes or the World Map. Pause, Settings, Help, and battle playback suspend kingdom simulation.
- Resizable scaled window, F11 fullscreen toggle, saved audio/FPS preferences, and startup support without an audio device.
- Atomic saves with a previous-version `.bak`, recovery from damaged saves, validation before changing live state, autosave on window close, and compatibility with existing v1 saves.
- New Game archives previous save slots instead of deleting them. Quest panels stay connected to the current kingdom after a reset.
- Corrected button/build-menu/training hitboxes, bounded list scrolling, modal input handling, and text-cache alpha/memory issues.

## Controls

| Control | Action |
| --- | --- |
| Left click | Select a building, collect its ready harvest, or place a structure |
| Right click | Cancel placement / close build and building-info panels |
| B | Build menu |
| C | Collect all ready harvest bonuses |
| U | Upgrade the selected building, including Barracks and Academy |
| T | Open troop training |
| R | Open Academy research |
| A | Army overview |
| H | Heroes and equipment |
| W | World Map |
| Q | Quests |
| F1 | How to Play |
| F5 | Save to the manual slot from the kingdom screen |
| F11 | Toggle fullscreen from any screen |
| Esc | Close the current panel, go back, or pause |
| Left / Right or mouse wheel | Scroll the campaign map |
| Space in battle | Skip playback / continue after results |

The 1x button in battle cycles through 1x, 2x, and 4x playback.

## First steps

Build a Carrot Farm and Lumber Burrow. Select your Castle and upgrade it to level 2, then build a Stone Quarry and Gold Mine. Warehouses increase the capacity of every resource. At Castle level 3, build a Barracks and train soldiers. Inspect campaign power recommendations before attacking. Claim completed quests to accelerate your growth. At Castle level 5, build the Academy and research permanent improvements.

Resource buildings produce automatically while operational. Every ten seconds, they prepare an additional harvest worth 15 resources per building level. Buildings stop producing while under construction or upgrading. Research and building costs are paid when work starts. Cancelling training refunds only untrained units; cancelling research refunds half its cost.

## Saves and settings

Source-run saves live in `bunny_lords/saves/`. Autosave runs every 60 seconds of active kingdom simulation, on Quit to Menu, and on window close. Closing during battle settles that battle's already-computed outcome before saving.

Each overwritten slot retains its previous contents in `<slot>.json.bak`. Continue tries the newest save, its backup, and then older slots. Invalid saves leave the current kingdom unchanged.

New Game copies existing slots into `saves/archive/<timestamp>/` before resetting the kingdom. To restore an archived kingdom, close the game, preserve your current slots, and copy the archived JSON into `saves/` as `manual_save.json`. The original v1 autosave bundled with this repository has been left intact.

Audio and FPS preferences live in `bunny_lords/preferences.json`. No network connection or external art download is needed to play. Offline time does not advance production.

## Development and verification

From the repository root:

```powershell
python -m unittest discover -s bunny_lords/tests -v
python -m compileall -q bunny_lords
```

The regression suite uses SDL's dummy video/audio drivers and temporary save directories. It covers the economy, training, quest identity and cooldowns, campaign restrictions, reward idempotency, save roundtrips/recovery, input hitboxes, modal isolation, and screen/battle rendering. It does not alter your existing saves. Native desktop fullscreen/resizing and audible sound still benefit from a manual playtest.

## Customize

All paths below are relative to `bunny_lords/`.

| File | Purpose |
| --- | --- |
| `data/buildings.json` | Explicit per-level costs, production, timers, unlocks, storage, and speed bonuses |
| `data/troops.json` | Troop tiers, stats, training costs/times, and Barracks requirements |
| `data/heroes.json`, `data/equipment.json` | Hero definitions, growth, abilities, and equipment |
| `data/research_tree.json` | Research costs, prerequisites, duration, and additive bonus fractions |
| `data/campaign.json` | Stage enemies, rewards, dependencies, and recommended power |
| `data/quests.json` | Achievement/daily event targets and rewards |
| `data/resources.json` | Starting resources and base capacities |
| `settings.py` | Display dimensions, colors, grid geometry, and timing |
| `ui/kingdom.py` | Dashboard, next-step guidance, resource HUD, and landscape |
| `utils/draw_helpers.py` | Procedural building and bunny illustrations |
| `systems/` | Economy, research, training, combat, quests, sound, and persistence |

Only explicitly defined building levels are available. Production bonuses are additive fractions (0.2 means +20%); capacity bonuses are flat additions. The legacy `build_exe.py` packaging helper is separate from source-run validation; a Windows executable was not rebuilt for this update.
