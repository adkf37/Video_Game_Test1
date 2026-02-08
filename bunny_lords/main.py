"""
Bunny Lords — Entry point.
Run with:  python main.py
"""
import sys
import os

# Ensure the bunny_lords package is on the path
sys.path.insert(0, os.path.dirname(__file__))

from core.game import Game


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
