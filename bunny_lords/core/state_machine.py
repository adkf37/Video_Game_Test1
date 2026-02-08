"""
State Machine — Screen / scene management with a stack.

Stack allows overlays (popups, modals) to sit on top of a base state.
Only the top-most state receives events; all visible states are drawn
bottom-to-top.
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


class StateManager:
    """Manages a stack of GameState instances."""

    def __init__(self):
        self._registry: dict[str, GameState] = {}
        self._stack: list[GameState] = []

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

    # -- queries --
    @property
    def current(self) -> GameState | None:
        return self._stack[-1] if self._stack else None

    @property
    def stack(self) -> list[GameState]:
        return self._stack

    # -- delegation helpers --
    def handle_event(self, event: pygame.event.Event):
        if self._stack:
            self._stack[-1].handle_event(event)

    def update(self, dt: float):
        if self._stack:
            self._stack[-1].update(dt)

    def draw(self, surface: pygame.Surface):
        """Draw all states; non-overlay states clear first."""
        for state in self._stack:
            state.draw(surface)
