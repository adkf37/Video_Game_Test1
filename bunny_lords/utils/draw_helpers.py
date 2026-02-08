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


def draw_building_shape(surface: pygame.Surface, rect: pygame.Rect,
                        color: tuple, building_id: str):
    """Draw a simple shape representing a building type inside *rect*."""
    pad = 6
    inner = rect.inflate(-pad * 2, -pad * 2)

    if building_id == "castle":
        # Castle: rectangle with battlements
        pygame.draw.rect(surface, color, inner, border_radius=4)
        # Battlements on top
        bw = inner.width // 5
        for i in range(0, 5, 2):
            br = pygame.Rect(inner.x + i * bw, inner.y - bw // 2, bw, bw // 2 + 2)
            pygame.draw.rect(surface, color, br)
        # Door
        door_w, door_h = inner.width // 4, inner.height // 3
        door_rect = pygame.Rect(inner.centerx - door_w // 2,
                                inner.bottom - door_h, door_w, door_h)
        pygame.draw.rect(surface, (40, 40, 60), door_rect, border_radius=3)

    elif building_id == "carrot_farm":
        # Farm: rect with a carrot triangle on top
        base = inner.inflate(0, -inner.height // 3)
        base.bottom = inner.bottom
        pygame.draw.rect(surface, (100, 70, 40), base, border_radius=3)
        # Carrot triangles
        for i in range(3):
            bx = inner.x + inner.width // 4 * (i + 0.5)
            pts = [(bx, inner.y + inner.height // 4),
                   (bx - 6, inner.y + inner.height * 0.6),
                   (bx + 6, inner.y + inner.height * 0.6)]
            pygame.draw.polygon(surface, color, pts)
            # Green top
            pygame.draw.line(surface, (60, 180, 60),
                             (bx, inner.y + inner.height // 4 - 6),
                             (bx, inner.y + inner.height // 4), 2)

    elif building_id in ("lumber_burrow", "stone_quarry", "gold_mine", "warehouse"):
        # Generic resource building: filled rect with icon letter
        pygame.draw.rect(surface, color, inner, border_radius=5)
        dark = tuple(max(c - 60, 0) for c in color)
        pygame.draw.rect(surface, dark, inner, width=2, border_radius=5)

    elif building_id == "barracks":
        # Barracks: rect with crossed swords (simple X)
        pygame.draw.rect(surface, color, inner, border_radius=5)
        c = inner.center
        s = inner.width // 4
        pygame.draw.line(surface, (255, 255, 255), (c[0]-s, c[1]-s), (c[0]+s, c[1]+s), 3)
        pygame.draw.line(surface, (255, 255, 255), (c[0]+s, c[1]-s), (c[0]-s, c[1]+s), 3)

    elif building_id == "academy":
        # Academy: triangle roof on rect
        base_h = inner.height * 2 // 3
        base_rect = pygame.Rect(inner.x, inner.bottom - base_h,
                                inner.width, base_h)
        pygame.draw.rect(surface, color, base_rect, border_radius=3)
        # Triangle roof
        pts = [(inner.centerx, inner.y),
               (inner.x, inner.bottom - base_h),
               (inner.right, inner.bottom - base_h)]
        pygame.draw.polygon(surface, tuple(min(c + 40, 255) for c in color), pts)

    elif building_id == "wall":
        # Wall: thick horizontal bar
        wall_rect = inner.inflate(0, -inner.height // 2)
        pygame.draw.rect(surface, color, wall_rect, border_radius=2)
        # Brick lines
        for y_off in range(0, wall_rect.height, 8):
            pygame.draw.line(surface, (100, 100, 110),
                             (wall_rect.x, wall_rect.y + y_off),
                             (wall_rect.right, wall_rect.y + y_off), 1)
    else:
        # Fallback: simple colored rect
        pygame.draw.rect(surface, color, inner, border_radius=5)


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
