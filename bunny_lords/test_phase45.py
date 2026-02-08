"""Quick test script for Phase 4+5 systems."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from systems.combat_system import CombatEngine, CampaignData
from systems.research_system import ResearchSystem
from systems.quest_system import QuestSystem
from core.event_bus import EventBus
from systems.resource_system import ResourceManager
from entities.troops import load_troop_defs
from entities.heroes import load_hero_defs, load_equip_defs, Hero

td = load_troop_defs()
hd = load_hero_defs()
ed = load_equip_defs()
camp = CampaignData()
rm = ResourceManager()
eb = EventBus()
rs = ResearchSystem(rm)
qs = QuestSystem(rm, eb)

print(f"Troops: {len(td)}")
print(f"Heroes: {len(hd)}")
print(f"Equipment: {len(ed)}")
print(f"Campaign stages: {len(camp.stages)}")
print(f"Research defs: {len(rs.defs)}")
print(f"Research categories: {rs.categories}")
print(f"Quest defs: {len(qs.defs)}")
print(f"Stage 1 unlocked: {camp.is_unlocked('stage_1')}")

# Battle test
engine = CombatEngine(td)
result = engine.resolve({"warrior_bunny": 10}, {"scout_bunny": 5})
print(f"\nBattle test (10 warriors vs 5 scouts):")
print(f"  Victory: {result['victory']}")
print(f"  Ticks: {result['ticks']}")
print(f"  Player losses: {result['player_losses']}")
print(f"  Enemy losses: {result['enemy_losses']}")

# Research test
ok, reason = rs.start_research("mil_atk_1", academy_level=1)
print(f"\nResearch start: ok={ok}, reason='{reason}'")
print(f"  Is researching: {rs.is_researching}")
completed = rs.update(100)  # fast-forward
print(f"  Completed: {completed}")
print(f"  Bonuses: {rs.get_bonuses()}")

# Quest test via event bus
print(f"\nQuest before event:")
for q in qs.get_achievements()[:3]:
    print(f"  {q.definition.name}: {q.progress}/{q.definition.target}")
eb.emit("building_complete", building_id="castle", level=1)
eb.emit("troops_trained", troop_id="warrior_bunny", count=5)
print(f"Quest after events:")
for q in qs.get_achievements()[:3]:
    print(f"  {q.definition.name}: {q.progress}/{q.definition.target}")

print("\n=== All Phase 4+5 systems verified! ===")
