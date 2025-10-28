#!/usr/bin/env python3
"""
wiz_discover_and_effects.py - Legacy entry point

This file now serves as a wrapper to the new modular wiz_lights package.
For the new modular structure, see src/wiz_lights/

Usage:
    uv run wiz_discover_and_effects.py
    
Or use the package directly:
    uv run wiz-lights
    python -m wiz_lights
"""

if __name__ == "__main__":
    from wiz_lights import main
    main()
