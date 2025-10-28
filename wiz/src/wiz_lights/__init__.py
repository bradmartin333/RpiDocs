"""
WIZ Lights Control Package

A Python package for discovering and controlling WIZ smart lights on your local network.

Features:
- Network discovery of WIZ lights (no broadcasts)
- 13 different control modes including rainbow effects, themed effects, nature simulations
- Interactive TUI (Text User Interface) with arrow-key navigation
- Configuration and caching support
- Modular design for easy extension

Usage:
    python -m wiz_lights
    
Or after installation:
    wiz-lights
"""

from .__main__ import main

__version__ = "0.1.0"
__all__ = ["main"]

