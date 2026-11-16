"""
Bunny Lords — Global Settings & Constants
"""

# ── Display ──────────────────────────────────────────────
SCREEN_WIDTH = 1400
SCREEN_HEIGHT = 800
FPS = 60
GAME_TITLE = "Bunny Lords"

# ── Grid / Base ──────────────────────────────────────────
GRID_COLS = 8
GRID_ROWS = 8
TILE_SIZE = 68          # pixels per tile
GRID_OFFSET_X = 40      # left margin for the grid on screen
GRID_OFFSET_Y = 164      # top margin (below resource bar)

# ── Colours (RGB) ────────────────────────────────────────
COLOR_BG           = (19, 31, 38)
COLOR_PANEL        = (30, 47, 54)
COLOR_PANEL_LIGHT  = (45, 65, 70)
COLOR_ACCENT       = (239, 192, 110)   # golden
COLOR_ACCENT2      = (132, 204, 161)  # teal / green
COLOR_DANGER       = (220, 60,  60)
COLOR_TEXT          = (239, 239, 221)
COLOR_TEXT_DIM      = (154, 177, 175)
COLOR_GRID_LINE    = (62, 94, 75)
COLOR_GRID_EMPTY   = (49, 84, 63)
COLOR_BUTTON       = (70,  130, 220)
COLOR_BUTTON_HOVER = (90,  150, 240)
COLOR_HP_GREEN     = (80,  200, 80)
COLOR_HP_RED       = (200, 60,  60)
COLOR_BLACK        = (0,   0,   0)
COLOR_WHITE        = (255, 255, 255)

# ── Resource colours ─────────────────────────────────────
RESOURCE_COLORS = {
    "carrots": (255, 140, 30),
    "wood":    (160, 110, 60),
    "stone":   (170, 170, 180),
    "gold":    (255, 215, 0),
}

# ── Building colours (by id) ────────────────────────────
BUILDING_COLORS = {
    "castle":       (180, 160, 220),
    "carrot_farm":  (255, 140, 30),
    "lumber_burrow":(120, 180, 80),
    "stone_quarry": (160, 160, 175),
    "gold_mine":    (255, 215, 0),
    "barracks":     (200, 70,  70),
    "academy":      (80,  140, 220),
    "wall":         (130, 130, 140),
    "warehouse":    (170, 130, 90),
}

# ── Timing ───────────────────────────────────────────────
AUTOSAVE_INTERVAL = 60.0   # seconds
RESOURCE_TICK     = 1.0    # seconds between resource production ticks

# ── Troop type colours ───────────────────────────────────
TROOP_TYPE_COLORS = {
    "infantry": (200, 140, 140),
    "cavalry":  (220, 180, 100),
    "ranged":   (140, 200, 220),
    "siege":    (180, 140, 100),
}

# ── Research category colours ────────────────────────────
RESEARCH_COLORS = {
    "economy":  (255, 200, 80),
    "military": (220, 80, 80),
    "defense":  (120, 180, 220),
    "hero":     (180, 140, 255),
}

# ── Campaign / map colours ───────────────────────────────
COLOR_MAP_BG       = (25, 30, 45)
COLOR_NODE_LOCKED  = (90, 90, 100)
COLOR_NODE_UNLOCKED = (239, 192, 110)
COLOR_NODE_CLEARED = (132, 204, 161)

# ── Fonts (sizes) ────────────────────────────────────────
FONT_SM = 16
FONT_MD = 22
FONT_LG = 32
FONT_XL = 48
FONT_TITLE = 64
