"""
Asset Loader — centralised sprite / font / sound loading with caching.

All images are .convert_alpha()'d at load time.  Fonts are cached by
(name, size) tuple.  Sounds are cached by path.
"""
import os
import pygame

_image_cache: dict[str, pygame.Surface] = {}
_font_cache: dict[tuple[str | None, int], pygame.Font] = {}
_sound_cache: dict[str, pygame.mixer.Sound] = {}

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")


def _full(subpath: str) -> str:
    return os.path.join(ASSETS_DIR, subpath)


# ── Images ───────────────────────────────────────────────
def load_image(subpath: str, scale: tuple[int, int] | None = None) -> pygame.Surface:
    key = f"{subpath}|{scale}"
    if key not in _image_cache:
        path = _full(subpath)
        img = pygame.image.load(path).convert_alpha()
        if scale:
            img = pygame.transform.smoothscale(img, scale)
        _image_cache[key] = img
    return _image_cache[key]


def make_surface(w: int, h: int, color: tuple, alpha: int = 255) -> pygame.Surface:
    """Create a simple filled rectangle surface (no file needed)."""
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill((*color[:3], alpha))
    return surf


# ── Fonts ────────────────────────────────────────────────
def get_font(size: int, name: str | None = None) -> pygame.font.Font:
    key = (name, size)
    if key not in _font_cache:
        if name:
            path = _full(f"fonts/{name}")
            _font_cache[key] = pygame.font.Font(path, size)
        else:
            _font_cache[key] = pygame.font.SysFont("segoeui", size)
    return _font_cache[key]


# ── Text rendering with cache ────────────────────────────
_text_cache: dict[tuple, pygame.Surface] = {}


def render_text(text: str, size: int, color: tuple = (240, 240, 240),
                font_name: str | None = None, bold: bool = False) -> pygame.Surface:
    key = (text, size, color, font_name, bold)
    if key not in _text_cache:
        font = get_font(size, font_name)
        font.set_bold(bold)
        _text_cache[key] = font.render(text, True, color)
        font.set_bold(False)
    return _text_cache[key]


def clear_text_cache():
    _text_cache.clear()


# ── Sounds ───────────────────────────────────────────────
def load_sound(subpath: str) -> pygame.mixer.Sound:
    if subpath not in _sound_cache:
        path = _full(subpath)
        _sound_cache[subpath] = pygame.mixer.Sound(path)
    return _sound_cache[subpath]
