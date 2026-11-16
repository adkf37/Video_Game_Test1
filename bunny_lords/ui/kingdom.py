"""Procedural landscape and live kingdom dashboard. No external art required."""
import math
import random
import pygame
import settings as S
from utils.asset_loader import render_text
from utils.draw_helpers import draw_bunny_icon, draw_building_shape, draw_progress_bar


def label(surface, text, pos, size=16, color=None, bold=False):
    surface.blit(render_text(text, size, color or S.COLOR_TEXT, bold=bold), pos)


def card(surface, rect, color=None):
    rect = pygame.Rect(rect)
    pygame.draw.rect(surface, (11, 23, 28), rect.move(0, 4), border_radius=14)
    pygame.draw.rect(surface, color or S.COLOR_PANEL, rect, border_radius=14)
    pygame.draw.rect(surface, (53, 75, 76), rect, 1, border_radius=14)


def tree(surface, x, y, size=24):
    pygame.draw.ellipse(surface, (28, 57, 49), (x-size, y+size//2, size*2, size//2))
    pygame.draw.rect(surface, (113, 84, 59), (x-3, y, 6, size))
    pygame.draw.circle(surface, (40, 92, 65), (x, y), size)
    pygame.draw.circle(surface, (57, 116, 77), (x-5, y-6), max(3, size-7))
    pygame.draw.circle(surface, (82, 138, 86), (x-7, y-10), max(2, size//3))


def landscape(width, height, seed=8):
    """Generate a cached, deterministic woodland illustration."""
    surface = pygame.Surface((width, height))
    rng = random.Random(seed)
    for y in range(height):
        t = y / height
        pygame.draw.line(surface, (int(28+15*t), int(63+27*t), int(66+7*t)), (0,y), (width,y))
    for i in range(4):
        points = [(0, height)]
        for x in range(0, width+25, 24):
            y = height * (.25 + i*.17) + math.sin(x/150+i*2)*50
            points.append((x, y))
        points.append((width, height))
        pygame.draw.polygon(surface, [(35,78,69),(42,91,70),(52,104,75),(63,116,79)][i], points)
    for _ in range(65):
        x, y = rng.randrange(width), rng.randrange(int(height*.35), height)
        tree(surface, x, y, rng.randint(10, 25))
    return surface


class KingdomDashboard:
    def __init__(self, base):
        self.base = base

    def objective(self):
        b = self.base
        ids = {v.id for v in b.buildings}
        castle = b._get_castle()
        level = castle.level if castle else 1
        if "carrot_farm" not in ids:
            return "Plant the first seeds", "Build a Carrot Farm to feed your growing kingdom.", "Press B, choose a farm, then choose an empty plot."
        if "lumber_burrow" not in ids:
            return "Put down roots", "Build a Lumber Burrow for a steady supply of wood.", "Production continues while you explore your kingdom."
        if level < 2:
            return "A little room to grow", "Upgrade your Castle to level 2 to unlock stone and gold.", "Select your castle, then choose Upgrade or press U."
        if "stone_quarry" not in ids or "gold_mine" not in ids:
            return "Build a thriving economy", "Add a Stone Quarry and Gold Mine to your village.", "Four resource types fuel construction, research, and troops."
        if level < 3:
            return "Prepare for adventure", "Upgrade your Castle to level 3 to unlock the Barracks.", "Collect glowing building bonuses with C."
        if "barracks" not in ids or b.army.total_count < 10:
            return "Rally the bunny brigade", "Build a Barracks and train your first ten soldiers.", "Press T to train. Select a building and press U to upgrade."
        if not b.campaign.completed:
            return "Beyond the burrow", "Your army is ready for its first campaign expedition.", "Press W to explore. Check recommended power before battle."
        if level < 5:
            return "A kingdom of possibilities", "Grow your Castle to level 5 and open the Academy.", "Warehouses expand storage; research improves your economy."
        return "Write your kingdom's story", "Research, train, and conquer the remaining campaign stages.", "Claim achievements in Quests to earn resources and hero XP."

    def draw(self, surface):
        b = self.base
        x, w = 652, 708
        castle = b._get_castle()
        label(surface, "THE BURROW", (40, 103), 14, S.COLOR_ACCENT, True)
        label(surface, "Your little kingdom", (40, 123), 23, bold=True)
        label(surface, "KINGDOM OVERVIEW", (x, 103), 14, S.COLOR_ACCENT, True)
        label(surface, "Small paws. Grand ambitions.", (x, 124), 26, bold=True)
        metrics = [("CASTLE", f"Level {castle.level if castle else 1}"),
                   ("ARMY", f"{b.army.total_count:,} troops"),
                   ("CAMPAIGN", f"{len(b.campaign.completed)} / {len(b.campaign.stages)} cleared")]
        for i, (title, value) in enumerate(metrics):
            mx = x + i*240
            card(surface, (mx, 177, 228, 78))
            label(surface, title, (mx+18, 189), 12, S.COLOR_TEXT_DIM, True)
            label(surface, value, (mx+18, 210), 24, bold=True)
        title, body, hint = self.objective()
        card(surface, (x, 275, w, 132), (39, 64, 60))
        label(surface, "YOUR NEXT CHAPTER", (x+22, 291), 12, S.COLOR_ACCENT, True)
        label(surface, title, (x+22, 310), 26, bold=True)
        label(surface, body, (x+22, 348), 17)
        label(surface, hint, (x+22, 376), 14, S.COLOR_TEXT_DIM)

        card(surface, (x, 427, w, 190))
        label(surface, "IN THE WORKS", (x+22, 444), 12, S.COLOR_ACCENT, True)
        jobs = [(f"{v.name}  /  Level {v._pending_level}", v.build_timer, v.build_progress)
                for v in b.buildings if v.building]
        for job in b.training_system.queue:
            jobs.append((f"{job.troop_def.name}  /  {job.remaining} remaining",
                         job.timer + (job.remaining-1)*job.time_per_unit, job.progress))
        research = b.research_system
        if research.current:
            jobs.append((research.defs[research.current].name, research.timer,
                         1-research.timer/max(1,research.total_time)))
        if not jobs:
            label(surface, "A peaceful moment in the burrow.", (x+22, 482), 21)
            label(surface, "Build something new, train troops, or plan your next expedition.",
                  (x+22, 520), 16, S.COLOR_TEXT_DIM)
        for i, (name, seconds, progress) in enumerate(jobs[:3]):
            y = 474+i*41
            label(surface, name, (x+22, y), 15)
            label(surface, f"{math.ceil(seconds)}s", (x+w-74, y), 14, S.COLOR_ACCENT)
            draw_progress_bar(surface, pygame.Rect(x+22, y+25, w-44, 4), progress,
                              S.COLOR_ACCENT2, S.COLOR_PANEL_LIGHT)
        if len(jobs)>3:
            label(surface, f"+{len(jobs)-3} more queued", (x+w-160,444), 13, S.COLOR_TEXT_DIM)
        ready = sum(v.click_available and not v.building for v in b.buildings)
        label(surface, f"{ready} harvest bonuses ready" if ready else "Your harvest bonuses are growing...",
              (x, 674), 14, S.COLOR_TEXT_DIM)
        label(surface, "B  Build    T  Train    U  Upgrade    C  Collect    F5  Save    F11  Fullscreen",
              (40, 718), 13, S.COLOR_TEXT_DIM)


def draw_resource_bar(surface, manager):
    pygame.draw.rect(surface, (19, 32, 39), (0,0,S.SCREEN_WIDTH,84))
    label(surface, "BUNNY", (24,14), 21, S.COLOR_ACCENT, True)
    label(surface, "LORDS", (24,39), 21, S.COLOR_TEXT, True)
    for i, rid in enumerate(manager.resource_names):
        x = 178+i*300
        color = S.RESOURCE_COLORS[rid]
        amount, cap = manager.get(rid), manager.capacity[rid]
        pygame.draw.circle(surface, color, (x+10,33), 7)
        label(surface, rid.upper(), (x+28,12), 12, color, True)
        label(surface, f"{int(amount):,}", (x+28,29), 24, bold=True)
        label(surface, f"/ {int(cap):,}", (x+132,36), 13, S.COLOR_TEXT_DIM)
        rate = manager.rates.get(rid, 0)
        label(surface, "FULL" if amount>=cap else f"+{rate:g}/s", (x+222,34), 13,
              S.COLOR_ACCENT if amount>=cap else S.COLOR_ACCENT2)
        draw_progress_bar(surface, pygame.Rect(x+28,65,246,3), amount/max(1,cap), color, S.COLOR_PANEL_LIGHT)
