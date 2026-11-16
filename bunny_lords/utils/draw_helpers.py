"""
Drawing helpers — procedural bunny shapes, icons, common primitives.
"""
import pygame
import math


def draw_bunny_icon(surface: pygame.Surface, rect: pygame.Rect,
                    color: tuple = (220, 220, 220), facing: str = "front"):
    """Draw a simple bunny silhouette (circle head + triangle ears) inside *rect*."""
    cx, cy = rect.centerx, rect.centery
    r = min(rect.width, rect.height) // 3

    # Body / head circle
    pygame.draw.circle(surface, color, (cx, cy + r // 4), r)

    # Ears
    ear_h = int(r * 1.4)
    ear_w = r // 3
    # Left ear
    pygame.draw.ellipse(surface, color,
                        (cx - ear_w - ear_w // 2, cy - r - ear_h + r // 3,
                         ear_w, ear_h))
    # Right ear
    pygame.draw.ellipse(surface, color,
                        (cx + ear_w // 2, cy - r - ear_h + r // 3,
                         ear_w, ear_h))

    # Inner ear (pink)
    inner = (255, 180, 180)
    iw, ih = max(ear_w - 4, 2), max(ear_h - 8, 2)
    pygame.draw.ellipse(surface, inner,
                        (cx - ear_w - ear_w // 2 + 2, cy - r - ear_h + r // 3 + 4,
                         iw, ih))
    pygame.draw.ellipse(surface, inner,
                        (cx + ear_w // 2 + 2, cy - r - ear_h + r // 3 + 4,
                         iw, ih))

    # Eyes
    pygame.draw.circle(surface, (30, 30, 30), (cx - r // 3, cy), max(r // 6, 2))
    pygame.draw.circle(surface, (30, 30, 30), (cx + r // 3, cy), max(r // 6, 2))

    # Nose
    pygame.draw.circle(surface, (255, 150, 150), (cx, cy + r // 4), max(r // 8, 2))


_building_art = {}


def draw_building_shape(surface: pygame.Surface, rect: pygame.Rect,
                        color: tuple, building_id: str):
    """Scale cached illustrated buildings, with distinct silhouettes at tile size."""
    key = (building_id, tuple(color), rect.size)
    if key not in _building_art:
        art = pygame.Surface((96,96), pygame.SRCALPHA)
        dark = tuple(max(0,c-45) for c in color)
        light = tuple(min(255,c+28) for c in color)
        ink = (36,45,46)
        pygame.draw.ellipse(art, (13,32,26,100), (9,74,80,16))
        if building_id == "castle":
            pygame.draw.rect(art, dark, (18,38,62,43), border_radius=3)
            pygame.draw.rect(art, color, (22,34,50,43))
            for x in (10,65):
                pygame.draw.rect(art, color, (x,29,22,53), border_radius=3)
                pygame.draw.rect(art, light, (x,29,6,47))
                pygame.draw.rect(art, dark, (x,30,22,5))
                for k in (0,8,16):
                    pygame.draw.rect(art, light, (x+k,22,6,12))
                pygame.draw.rect(art, ink, (x+8,44,6,11), border_radius=3)
            pygame.draw.rect(art, ink, (39,58,18,24), border_top_left_radius=9, border_top_right_radius=9)
            pygame.draw.rect(art, (145,105,65), (43,64,10,18), border_top_left_radius=5, border_top_right_radius=5)
            pygame.draw.line(art, (224,202,149), (49,12),(49,37),2)
            pygame.draw.polygon(art,(231,176,94),[(50,12),(68,17),(50,23)])
            pygame.draw.line(art,light,(33,47),(62,47),2)
        elif building_id == "carrot_farm":
            pygame.draw.polygon(art, (100,72,48), [(9,38),(71,32),(88,77),(22,86)])
            for row in range(3):
                y=44+row*12
                pygame.draw.line(art,(66,50,37),(17,y+6),(78,y),3)
                for col in range(3):
                    x=25+col*20+row*3
                    pygame.draw.polygon(art,(241,153,60),[(x-4,y),(x+5,y),(x,y+12)])
                    pygame.draw.line(art,(134,188,82),(x,y),(x-4,y-8),3)
                    pygame.draw.line(art,(91,162,77),(x,y),(x+4,y-9),3)
            for x in (12,78):
                pygame.draw.rect(art,(193,160,105),(x,59,4,25))
            pygame.draw.line(art,(193,160,105),(12,72),(81,72),3)
        elif building_id == "lumber_burrow":
            for x,y,r in [(25,34,19),(66,29,21)]:
                pygame.draw.rect(art,(133,94,61),(x-4,y,8,38))
                pygame.draw.circle(art,dark,(x,y),r)
                pygame.draw.circle(art,color,(x-4,y-5),r-5)
                pygame.draw.circle(art,light,(x-8,y-8),r//3)
            for x,y in [(29,70),(49,75),(63,66)]:
                pygame.draw.line(art,(143,102,65),(x-14,y-5),(x+10,y+4),11)
                pygame.draw.circle(art,(217,184,121),(x+10,y+4),6)
                pygame.draw.circle(art,(151,112,74),(x+10,y+4),3,1)
        elif building_id in ("stone_quarry", "gold_mine"):
            pygame.draw.polygon(art,dark,[(8,80),(20,46),(37,37),(45,17),(67,23),(87,79)])
            pygame.draw.polygon(art,color,[(20,46),(37,37),(45,17),(52,56),(38,80),(8,80)])
            pygame.draw.polygon(art,light,[(45,17),(67,23),(54,37)])
            pygame.draw.rect(art,ink,(46,56,24,26),border_top_left_radius=12,border_top_right_radius=12)
            pygame.draw.lines(art,(149,112,75),False,[(43,82),(43,53),(73,53),(73,82)],5)
            for x,y in [(20,72),(31,61),(76,75)]:
                pygame.draw.polygon(art,(239,194,81) if building_id == "gold_mine" else (192,201,190),
                                    [(x,y-5),(x+8,y-2),(x+6,y+5),(x-3,y+3)])
        elif building_id == "wall":
            pygame.draw.rect(art,dark,(9,42,78,40))
            pygame.draw.rect(art,color,(9,38,78,34))
            for y in range(40,75,11):
                pygame.draw.line(art,dark,(10,y),(86,y),2)
                for x in range(12+(y%2)*10,86,20):
                    pygame.draw.line(art,dark,(x,y),(x,y+10),2)
            for x in range(9,85,16):
                pygame.draw.rect(art,light,(x,27,10,14))
        else:
            pygame.draw.rect(art,dark,(16,43,65,39),border_radius=3)
            pygame.draw.rect(art,color,(16,43,58,34))
            pygame.draw.polygon(art,dark,[(9,45),(46,15),(87,45)])
            pygame.draw.polygon(art,light,[(9,45),(46,15),(75,45)])
            pygame.draw.line(art,(229,209,165),(9,45),(46,15),3)
            pygame.draw.rect(art,ink,(40,57,16,25),border_top_left_radius=7,border_top_right_radius=7)
            for x in (23,63):
                pygame.draw.rect(art,(238,211,135),(x,53,9,12),border_radius=2)
                pygame.draw.line(art,dark,(x+4,53),(x+4,65),1)
            if building_id == "academy":
                pygame.draw.circle(art,(232,216,172),(46,34),8)
                pygame.draw.circle(art,ink,(46,34),5)
                pygame.draw.line(art,(232,216,172),(46,34),(46,30),1)
                pygame.draw.line(art,(232,216,172),(46,34),(49,36),1)
            elif building_id == "barracks":
                pygame.draw.line(art,(230,217,183),(33,29),(57,47),4)
                pygame.draw.line(art,(230,217,183),(57,29),(33,47),4)
            elif building_id == "warehouse":
                for x in (19,62):
                    pygame.draw.rect(art,(195,155,95),(x,70,18,15),border_radius=2)
                    pygame.draw.rect(art,(102,78,51),(x,70,18,15),1)
                    pygame.draw.line(art,(102,78,51),(x,70),(x+18,85),2)
        if len(_building_art)>512:
            _building_art.clear()
        _building_art[key] = pygame.transform.smoothscale(art,rect.size)
    surface.blit(_building_art[key], rect)


def draw_progress_bar(surface: pygame.Surface, rect: pygame.Rect,
                      progress: float, fg_color: tuple = (80, 200, 80),
                      bg_color: tuple = (50, 50, 60), border_color: tuple | None = None):
    """Draw a horizontal progress bar. progress is 0.0 – 1.0."""
    progress = max(0.0, min(1.0, progress))
    pygame.draw.rect(surface, bg_color, rect, border_radius=3)
    if progress > 0:
        fill_rect = pygame.Rect(rect.x, rect.y,
                                int(rect.width * progress), rect.height)
        pygame.draw.rect(surface, fg_color, fill_rect, border_radius=3)
    if border_color:
        pygame.draw.rect(surface, border_color, rect, width=1, border_radius=3)


def draw_rounded_panel(surface: pygame.Surface, rect: pygame.Rect,
                       color: tuple, border_color: tuple | None = None,
                       radius: int = 8, alpha: int = 230):
    """Draw a semi-transparent rounded panel."""
    panel = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*color[:3], alpha),
                     (0, 0, rect.width, rect.height), border_radius=radius)
    if border_color:
        pygame.draw.rect(panel, (*border_color[:3], 255),
                         (0, 0, rect.width, rect.height),
                         width=2, border_radius=radius)
    surface.blit(panel, rect.topleft)
