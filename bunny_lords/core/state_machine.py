"""
State Machine — Screen / scene management with a stack.

Stack allows overlays (popups, modals) to sit on top of a base state.
Only the top-most state receives events; all visible states are drawn
bottom-to-top.  Includes fade transitions between states.
"""
from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from core.game import Game


class GameState:
    """Base class for every screen / overlay in the game."""

    IS_OVERLAY = False  # overlays don't clear the screen; drawn on top

    def __init__(self, game: "Game"):
        self.game = game

    # -- lifecycle --
    def enter(self, **params):
        """Called when this state is pushed / becomes active."""
        pass

    def exit(self):
        """Called when this state is popped."""
        pass

    # -- per-frame --
    def handle_event(self, event: pygame.event.Event):
        pass

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass


class Transition:
    """Fade-to-black transition between states."""

    DURATION = 0.3  # total duration (fade out + fade in)

    def __init__(self):
        self.active = False
        self.timer = 0.0
        self.alpha = 0         # 0 = transparent, 255 = fully black
        self._half = self.DURATION / 2
        self._callback = None  # called at mid-point (state swap)
        self._called = False
        self._overlay = None

    def start(self, callback):
        """Begin the transition. callback() is invoked at the midpoint."""
        self.active = True
        self.timer = 0.0
        self.alpha = 0
        self._callback = callback
        self._called = False

    def update(self, dt: float):
        if not self.active:
            return
        self.timer += dt
        if self.timer < self._half:
            # Fade out (0 → 255)
            self.alpha = int(255 * (self.timer / self._half))
        else:
            if not self._called and self._callback:
                self._callback()
                self._called = True
            # Fade in (255 → 0)
            t = self.timer - self._half
            self.alpha = int(255 * (1.0 - t / self._half))
        if self.timer >= self.DURATION:
            self.active = False
            self.alpha = 0

    def draw(self, surface: pygame.Surface):
        if not self.active or self.alpha <= 0:
            return
        if self._overlay is None or self._overlay.get_size() != surface.get_size():
            self._overlay = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
        self._overlay.fill((0, 0, 0, min(255, max(0, self.alpha))))
        surface.blit(self._overlay, (0, 0))


class StateManager:
    """Manages a stack of GameState instances."""

    def __init__(self):
        self._registry: dict[str, GameState] = {}
        self._stack: list[GameState] = []
        self.transition = Transition()

    # -- registration --
    def register(self, name: str, state: GameState):
        self._registry[name] = state

    # -- stack operations --
    def push(self, name: str, **params):
        state = self._registry[name]
        self._stack.append(state)
        state.enter(**params)

    def pop(self):
        if self._stack:
            self._stack[-1].exit()
            self._stack.pop()

    def replace(self, name: str, **params):
        """Pop current, push new."""
        self.pop()
        self.push(name, **params)

    def transition_to(self, name: str, **params):
        """Replace current state with a fade transition."""
        def swap():
            self.pop()
            self.push(name, **params)
        self.transition.start(swap)

    # -- queries --
    @property
    def current(self) -> GameState | None:
        return self._stack[-1] if self._stack else None

    @property
    def stack(self) -> list[GameState]:
        return self._stack

    # -- delegation helpers --
    def handle_event(self, event: pygame.event.Event):
        if self.transition.active:
            return  # block input during transitions
        if self._stack:
            self._stack[-1].handle_event(event)

    def update(self, dt: float):
        self.transition.update(dt)
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self, surface: pygame.Surface):
        """Draw all states; non-overlay states clear first."""
        for state in self._stack:
            state.draw(surface)
        self.transition.draw(surface)
