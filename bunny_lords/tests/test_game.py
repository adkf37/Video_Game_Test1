"""Headless regression coverage. All save mutations use temporary directories."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pygame
from core.game import Game
from systems import save_system
from systems.combat_system import CombatEngine
from ui.widgets import Button
from utils.asset_loader import render_text


def click(pos):
    return pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)


class GameRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.game = Game()
        cls.game.sound_manager.enabled = False

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.base = self.game.state_manager._registry["base_view"]
        self.base.reset_to_new_game()
        self.game.state_manager._stack[:] = [self.base]
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.save_patch = patch.object(save_system, "SAVE_DIR", self.temp.name)
        self.save_patch.start()
        self.addCleanup(self.save_patch.stop)

    def place(self, bid, x=0, y=0):
        return self.base._place_building(bid, x, y, instant=True)

    def fund(self):
        for resource in self.base.resource_mgr.resource_names:
            self.base.resource_mgr.resources[resource] = 10000

    def test_economy_uses_research_and_stacks_warehouse_capacity(self):
        farm = self.place("carrot_farm")
        warehouse = self.place("warehouse", 1)
        self.place("warehouse", 2)
        self.base.research_system.completed.update(["eco_carrots_1", "eco_capacity_1"])
        bonuses = self.base.research_system.get_bonuses()
        manager = self.base.resource_mgr
        before = manager.get("carrots")
        manager.apply_production(self.base.buildings, bonuses)
        self.assertEqual(manager.get("carrots") - before, 6)
        self.assertEqual(manager.capacity["carrots"], 16000)
        warehouse.start_build(2, 2)
        manager.refresh_economy(self.base.buildings, bonuses)
        self.assertEqual(manager.capacity["carrots"], 16000)
        warehouse.update(2)
        manager.refresh_economy(self.base.buildings, bonuses)
        self.assertEqual(manager.capacity["carrots"], 19000)
        farm.start_build(2, 1)
        manager.refresh_economy(self.base.buildings, bonuses)
        self.assertEqual(manager.rates["carrots"], 0)

    def test_training_carries_elapsed_time_and_counts_each_troop(self):
        self.fund()
        training = self.base.training_system
        tid = next(iter(training.troop_defs))
        training.start_training(tid, 2)
        duration = training.queue[0].time_per_unit
        training.start_training(tid, 2)
        self.assertEqual(training.update(duration), [(tid, 1)])
        self.assertEqual(training.update(duration*2.5), [(tid, 2)])
        self.assertEqual(self.base.army.total_count, 3)
        self.assertAlmostEqual(training.queue[0].timer, duration*.5)
        self.assertEqual(training.update(duration*.5), [(tid, 1)])
        self.assertFalse(training.queue)

    def test_invalid_training_cannot_generate_resources(self):
        training = self.base.training_system
        tid = next(iter(training.troop_defs))
        before = self.base.resource_mgr.to_dict()
        for count in (-5, 0, 1.5):
            self.assertFalse(training.start_training(tid, count))
        self.assertFalse(training.start_training(tid, 1, speed_mult=0))
        self.assertFalse(self.base.resource_mgr.pay({"gold": -100}))
        self.assertEqual(before, self.base.resource_mgr.to_dict())

    def test_cancel_refunds_only_untrained_units(self):
        training = self.base.training_system
        tid = next(iter(training.troop_defs))
        definition = training.troop_defs[tid]
        self.fund()
        before = self.base.resource_mgr.to_dict()["resources"]
        training.start_training(tid, 3)
        training.update(training.queue[0].time_per_unit)
        training.cancel_job(0)
        for rid, amount in definition.cost.items():
            self.assertEqual(self.base.resource_mgr.get(rid), before[rid]-amount)
        self.assertEqual(self.base.army.total_count, 1)

    def test_new_game_preserves_quest_identity_without_duplicate_listeners(self):
        original = self.base.quest_system
        listeners = len(self.game.event_bus._listeners["building_complete"])
        for _ in range(3):
            self.base.reset_to_new_game()
        self.assertIs(self.base.quest_panel.quest_system, original)
        self.assertEqual(len(self.game.event_bus._listeners["building_complete"]), listeners)
        self.game.event_bus.emit("building_complete", building_id="carrot_farm", level=1)
        for q in original.quests.values():
            if q.definition.track_type == "building_complete":
                self.assertEqual(q.progress, 1)

    def test_daily_badge_matches_actual_cooldown(self):
        quest = self.base.quest_system.get_dailies()[0]
        quest.progress = quest.definition.target
        with patch("time.time", return_value=100000):
            self.assertTrue(self.base.quest_system.claim(quest.id))
            quest.progress = quest.definition.target
            self.assertNotIn(quest, self.base.quest_system.get_claimable())
            self.assertFalse(self.base.quest_system.claim(quest.id))
        with patch("time.time", return_value=186400):
            self.assertIn(quest, self.base.quest_system.get_claimable())
            self.assertTrue(self.base.quest_system.claim(quest.id))

    def test_save_roundtrip_preserves_active_jobs_and_heroes(self):
        farm = self.place("carrot_farm")
        farm.start_build(2, 12)
        farm.update(3)
        self.base.heroes[0].add_xp(140)
        self.fund()
        tid = next(iter(self.base.troop_defs))
        self.base.training_system.start_training(tid, 3)
        self.base.training_system.update(1)
        expected_heroes = [h.to_dict() for h in self.base.heroes]
        expected_queue = self.base.training_system.to_list()
        path = save_system.save_game(self.base)
        self.base.reset_to_new_game()
        self.assertTrue(save_system.load_game(self.base, path))
        self.assertEqual(self.base.grid[0][0].build_timer, 9)
        self.assertEqual([h.to_dict() for h in self.base.heroes], expected_heroes)
        self.assertEqual(self.base.training_system.to_list(), expected_queue)
        self.assertIs(self.base.training_panel.training_system, self.base.training_system)

    def test_corrupt_load_does_not_modify_live_progress(self):
        self.place("carrot_farm")
        path = save_system.save_game(self.base)
        data = json.loads(Path(path).read_text())
        data["buildings"][1]["grid_x"] = -1
        Path(path).write_text(json.dumps(data))
        before = [b.to_dict() for b in self.base.buildings]
        self.assertFalse(save_system.load_game(self.base, path))
        self.assertEqual(before, [b.to_dict() for b in self.base.buildings])

    def test_save_recovers_previous_atomic_backup(self):
        self.base.resource_mgr.resources["gold"] = 123
        path = save_system.save_game(self.base)
        self.base.resource_mgr.resources["gold"] = 456
        save_system.save_game(self.base)
        Path(path).write_text("{broken")
        self.assertEqual(len(save_system.list_saves()), 1)
        self.assertTrue(save_system.load_game(self.base, path))
        self.assertEqual(self.base.resource_mgr.get("gold"), 123)

    def test_daily_v1_migration_and_campaign_replays(self):
        quest = self.base.quest_system.get_dailies()[0]
        self.base.quest_system.from_dict({quest.id: {"claimed": True, "last_claim_time": 1}})
        with patch("time.time", return_value=100000):
            self.base.quest_system.get_dailies()
            self.assertFalse(quest.claimed)
        campaign_quests = [q for q in self.base.quest_system.quests.values()
                           if q.definition.track_type == "campaign_complete"]
        self.game.event_bus.emit("campaign_complete", first_clear=True)
        self.game.event_bus.emit("campaign_complete", first_clear=False)
        for q in campaign_quests:
            self.assertEqual(q.progress, 1)

    def test_window_close_saves_and_settles_active_battle(self):
        tid = next(iter(self.base.troop_defs))
        self.base.army.add(tid, 40)
        self.base._open_world_map()
        self.game.state_manager.current._launch_battle()
        battle = self.game.state_manager.current
        self.game.save_on_exit()
        self.assertEqual(battle._phase, "result")
        self.assertTrue((Path(self.temp.name)/"autosave.json").exists())
        saved_army = self.base.army.to_dict()
        self.base.reset_to_new_game()
        self.assertTrue(save_system.load_game(self.base, str(Path(self.temp.name)/"autosave.json")))
        self.assertEqual(saved_army, self.base.army.to_dict())

    def test_existing_v1_save_loads(self):
        original = Path(__file__).resolve().parents[1] / "saves" / "autosave.json"
        if original.exists():
            self.assertTrue(save_system.load_game(self.base, str(original)))

    def test_button_uses_current_click_position(self):
        actions = []
        button = Button(pygame.Rect(10,10,100,40), "Test", lambda: actions.append(1))
        self.assertTrue(button.handle_event(click((20,20))))
        button.hover = True
        self.assertFalse(button.handle_event(click((500,500))))
        self.assertEqual(actions, [1])

    def test_build_menu_hitboxes_match_rows_and_ignore_header(self):
        panel = self.base.build_menu
        panel.show(["carrot_farm", "lumber_burrow"], 1)
        chosen = []
        with patch.object(panel, "on_select", chosen.append):
            panel.handle_event(click((panel.rect.x+70, panel.rect.y+46+69)))
            self.assertEqual(chosen, ["carrot_farm"])
            panel._scroll_y = 70
            panel.handle_event(click((panel.rect.x+70, panel.rect.y+12)))
            self.assertEqual(len(chosen), 1)

    def test_training_buttons_match_rendered_rows_and_queue(self):
        self.fund()
        panel = self.base.training_panel
        panel.show(5)
        panel.draw(self.game.screen)
        panel.handle_event(click((panel.rect.right-50, panel.rect.y+120)))
        self.assertEqual(len(self.base.training_system.queue), 1)
        panel.draw(self.game.screen)
        panel.handle_event(click((panel.rect.right-50, panel.rect.bottom-160)))
        self.assertFalse(self.base.training_system.queue)

    def test_modal_click_cannot_place_building_behind_it(self):
        self.base._placing = "carrot_farm"
        self.base.training_panel.show(1)
        self.base.handle_event(click(self.base._grid_to_screen(0,0).center))
        self.assertIsNone(self.base.grid[0][0])

    def test_harvest_scales_and_keeps_bonus_when_storage_full(self):
        farm = self.place("carrot_farm")
        farm.level = 2
        farm.click_available = True
        self.assertEqual(self.base._collect_bonus(farm), 30)
        farm.click_available = True
        self.base.resource_mgr.resources["carrots"] = self.base.resource_mgr.capacity["carrots"]
        self.assertEqual(self.base._collect_bonus(farm), 0)
        self.assertTrue(farm.click_available)

    def test_production_continues_on_map_but_pauses_in_pause_menu(self):
        self.place("carrot_farm")
        self.base._open_world_map()
        before = self.base.resource_mgr.get("carrots")
        self.game.state_manager.update(1)
        self.assertEqual(self.base.resource_mgr.get("carrots"), before+5)
        self.game.state_manager.push("pause_menu", base_view=self.base)
        self.game.state_manager.update(1)
        self.assertEqual(self.base.resource_mgr.get("carrots"), before+5)

    def test_locked_stage_cannot_launch_battle(self):
        self.base._open_world_map()
        world = self.game.state_manager.current
        world._selected = list(self.base.campaign.stages)[-1]
        self.base.army.add(next(iter(self.base.troop_defs)), 100)
        world._launch_battle()
        self.assertIs(self.game.state_manager.current, world)

    def test_battle_rewards_and_losses_are_applied_once(self):
        tid = next(iter(self.base.troop_defs))
        self.base.army.add(tid, 10)
        battle = self.game.state_manager._registry["battle_view"]
        stage_id = next(iter(self.base.campaign.stages))
        battle.enter(result={"victory": True, "player_losses": {tid: 2}},
                     army=self.base.army, resource_mgr=self.base.resource_mgr,
                     event_bus=self.game.event_bus, campaign=self.base.campaign,
                     stage_id=stage_id, stage_data={"rewards": {"gold": 100, "xp": 25}})
        gold, xp = self.base.resource_mgr.get("gold"), self.base.heroes[0].xp
        battle._end_battle()
        battle._end_battle()
        self.assertEqual(self.base.army.total_count, 8)
        self.assertEqual(self.base.resource_mgr.get("gold"), gold+100)
        self.assertEqual(self.base.heroes[0].xp, xp+25)

    def test_text_alpha_does_not_contaminate_cached_text(self):
        text = render_text("same text", 16)
        text.set_alpha(0)
        self.assertEqual(render_text("same text",16).get_alpha(), 255)

    def test_screens_and_full_battle_render(self):
        manager = self.game.state_manager
        for name in ("main_menu", "settings", "help_screen", "hero_management", "pause_menu"):
            state = manager._registry[name]
            state.enter(base_view=self.base)
            state.draw(self.game.screen)
        self.base.draw(self.game.screen)
        self.base._open_world_map()
        world = manager.current
        world.draw(self.game.screen)
        tid = next(iter(self.base.troop_defs))
        self.base.army.add(tid, 40)
        world._launch_battle()
        battle = manager.current
        battle.draw(self.game.screen)
        battle._skip_battle()
        battle.draw(self.game.screen)
        self.assertEqual(battle._phase, "result")


if __name__ == "__main__":
    unittest.main()
