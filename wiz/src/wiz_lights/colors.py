"""
Color conversion utilities for WIZ lights.
"""
import colorsys
import math
from typing import Tuple


def hsv_to_rgb_255(h_deg: float, s: float, v: float) -> Tuple[int, int, int]:
    """
    Convert HSV (h in degrees 0-360, s and v in 0-1) to RGB 0-255 ints.
    """
    h = (h_deg % 360) / 360.0
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def kelvin_to_rgb_255(kelvin: int) -> Tuple[int, int, int]:
    """
    Convert color temperature in Kelvin to RGB 0-255 ints.
    Based on algorithm from Tanner Helland.
    """
    # Clamp temperature to reasonable range
    temp = max(1000, min(40000, kelvin)) / 100.0
    
    # Calculate red
    if temp <= 66:
        r = 255
    else:
        r = temp - 60
        r = 329.698727446 * (r ** -0.1332047592)
        r = max(0, min(255, r))
    
    # Calculate green
    if temp <= 66:
        g = temp
        g = 99.4708025861 * math.log(g) - 161.1195681661
    else:
        g = temp - 60
        g = 288.1221695283 * (g ** -0.0755148492)
    g = max(0, min(255, g))
    
    # Calculate blue
    if temp >= 66:
        b = 255
    elif temp <= 19:
        b = 0
    else:
        b = temp - 10
        b = 138.5177312231 * math.log(b) - 305.0447927307
        b = max(0, min(255, b))
    
    return int(r), int(g), int(b)
