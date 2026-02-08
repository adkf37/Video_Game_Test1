"""
Camera — viewport for scrollable / pannable game views.
"""
import pygame


class Camera:
    """A rectangle representing the visible viewport in world space."""

    def __init__(self, view_w: int, view_h: int,
                 world_w: int = 0, world_h: int = 0):
        self.rect = pygame.Rect(0, 0, view_w, view_h)
        self.world_w = world_w
        self.world_h = world_h
        self._dragging = False
        self._drag_start = (0, 0)

    # -- coordinate conversion --
    def apply(self, world_rect: pygame.Rect) -> pygame.Rect:
        """World → screen."""
        return world_rect.move(-self.rect.x, -self.rect.y)

    def apply_pos(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx - self.rect.x), int(wy - self.rect.y)

    def screen_to_world(self, sx: int, sy: int) -> tuple[int, int]:
        """Screen → world."""
        return sx + self.rect.x, sy + self.rect.y

    # -- movement --
    def center_on(self, x: int, y: int):
        self.rect.center = (x, y)
        self._clamp()

    def move(self, dx: int, dy: int):
        self.rect.x += dx
        self.rect.y += dy
        self._clamp()

    def _clamp(self):
        if self.world_w and self.world_h:
            self.rect.clamp_ip(pygame.Rect(0, 0, self.world_w, self.world_h))

    # -- drag-to-pan (call from state's handle_event) --
    def handle_event(self, event: pygame.event.Event) -> bool:
        """Returns True if the camera consumed the event."""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 2:  # middle
            self._dragging = True
            self._drag_start = event.pos
            return True
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self._dragging = False
            return True
        if event.type == pygame.MOUSEMOTION and self._dragging:
            dx = self._drag_start[0] - event.pos[0]
            dy = self._drag_start[1] - event.pos[1]
            self.move(dx, dy)
            self._drag_start = event.pos
            return True
        return False
