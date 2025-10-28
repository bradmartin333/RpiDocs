#!/usr/bin/env python3
"""
wiz_discover_and_effects.py

Discover WIZ lights on the local network by probing configurable IP range (no broadcasts)
and provide simple effects:
 - rainbow_in_unison: all lights cycle through HSV colors in sync
 - rainbow: lights cycle through HSV colors with different offsets (not in unison)
 - spooky: a Halloween-ish effect (orange/purple flicker/pulse with occasional strobe)
 - white: reset lights to white at a specified color temperature in Kelvin
 - rgba: set custom RGBA color with dimming control
 - party: random colorful flashing party mode
 - synth: flash bulbs using number keys like a synthesizer
 - reactive: uses the microphone to control the lights based on audio levels
 - seasonal: applies color schemes based on the current date/season
 - danger: a scary red strobe effect
 - lightning: stormy skies with random lightning flashes
 - waterfall: turbulent blues and white flowing effect
 - fungi: a fun and funky psychedelic animation

Usage:
    python3 wiz_discover_and_effects.py

Notes:
 - This script probes each IP in the configured IP range (no UDP broadcast).
 - Probing is done by sending a small JSON query to UDP port 38899 and waiting
   briefly for a response. This is slower than broadcast discovery but avoids
   sending broadcast packets as requested.
 - Effects run in the background and can be changed by pressing Enter (no need for Ctrl+C).
 - Press Ctrl+C to exit the program completely.
 - Discovered bulbs are cached for faster startup. Use rescan option to refresh.
 - Reactive mode requires PyAudio library (install with: pip install pyaudio)
"""

import socket
import json
import time
import colorsys
import random
import concurrent.futures
import threading
import math
import os
import sys
import select
from datetime import datetime
from typing import Dict, List, Tuple, Optional

WIZ_PORT = 38899
PROBE_TIMEOUT = 0.35   # seconds to wait for a single probe response
SEND_INTERVAL = 0.12   # seconds between color updates (tweak for speed/CPU)

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "wiz_bulb_cache.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# A lightweight query that many WIZ bulbs will answer to
PROBE_PAYLOAD = {"method": "getPilot", "params": {}}

def load_config() -> dict:
    """Load configuration from config.json, return defaults if not found."""
    default_config = {"base_ip": "192.168.1"}
    if not os.path.exists(CONFIG_FILE):
        # Create default config file
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(default_config, f, indent=2)
            # Set restrictive permissions (owner read/write only)
            os.chmod(CONFIG_FILE, 0o600)
        except Exception as e:
            print(f"Warning: Could not create config file: {e}")
        return default_config
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            # Ensure base_ip exists
            if "base_ip" not in config:
                config["base_ip"] = "192.168.1"
            return config
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        return default_config

def save_cache(discovered: Dict[str, dict]) -> None:
    """Save discovered bulbs to cache file."""
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(discovered, f, indent=2)
        # Set restrictive permissions (owner read/write only)
        os.chmod(CACHE_FILE, 0o600)
    except Exception as e:
        print(f"Warning: Could not save cache: {e}")

def load_cache() -> Optional[Dict[str, dict]]:
    """Load cached bulbs from cache file. Returns None if cache doesn't exist or is invalid."""
    if not os.path.exists(CACHE_FILE):
        return None
    
    try:
        with open(CACHE_FILE, 'r') as f:
            cache = json.load(f)
            if isinstance(cache, dict) and cache:
                return cache
            return None
    except Exception as e:
        print(f"Warning: Could not load cache: {e}")
        return None


def probe_ip(ip: str, timeout: float = PROBE_TIMEOUT) -> Dict:
    """
    Probe a single IP by sending a JSON UDP request and waiting for a response.
    Returns parsed JSON dict if a response was received and parsed, otherwise None.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind to an ephemeral port so we can receive the reply on the same socket
    try:
        s.bind(("", 0))
    except Exception:
        pass
    s.settimeout(timeout)
    try:
        s.sendto(json.dumps(PROBE_PAYLOAD).encode("utf-8"), (ip, WIZ_PORT))
        data, addr = s.recvfrom(4096)
    except socket.timeout:
        return None
    except Exception:
        return None
    finally:
        try:
            s.close()
        except Exception:
            pass

    try:
        dec = data.decode("utf-8", errors="ignore")
        idx = dec.find("{")
        if idx != -1:
            dec = dec[idx:]
        obj = json.loads(dec)
        return obj
    except Exception:
        # return raw string if parsing failed
        try:
            return {"_raw": data.decode("utf-8", errors="ignore")}
        except Exception:
            return {"_raw": "<binary>"}

def scan_ip_range(base_ip: str = "192.168.1", start: int = 0, end: int = 255, workers: int = 60) -> Dict[str, dict]:
    """
    Scan the IPv4 range base_ip.start .. base_ip.end (inclusive) by probing each IP.
    Returns a dict mapping IP -> response dict for each responsive device.
    
    Args:
        base_ip: Base IP address (e.g., "192.168.1" for 192.168.1.0-255)
        start: Starting host number
        end: Ending host number (inclusive)
        workers: Number of concurrent threads for scanning
    """
    prefix = base_ip + "." if not base_ip.endswith(".") else base_ip
    ips = [f"{prefix}{i}" for i in range(start, end + 1)]
    discovered: Dict[str, dict] = {}

    # Use a thread pool to probe multiple addresses concurrently to speed up scanning
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        future_map = {ex.submit(probe_ip, ip): ip for ip in ips}
        for fut in concurrent.futures.as_completed(future_map):
            ip = future_map[fut]
            try:
                res = fut.result()
            except Exception:
                res = None
            if res:
                discovered[ip] = res
    return discovered

def send_udp(ip: str, payload: dict) -> None:
    """
    Send a JSON payload to a device IP over UDP (WIZ uses 38899).
    Fire-and-forget; some devices don't reply to setPilot, so we don't wait here.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(0.5)
    try:
        s.sendto(json.dumps(payload).encode("utf-8"), (ip, WIZ_PORT))
    except Exception:
        pass
    finally:
        try:
            s.close()
        except Exception:
            pass

def set_color_rgb(ip: str, r: int, g: int, b: int, transition: int = 0, dimming: int = 100) -> None:
    """
    Tell a WIZ light to set color using RGB values (0-255).
    Uses method 'setPilot' which is commonly supported by WIZ lights.
    transition is transition time in milliseconds (device dependent).
    dimming is brightness level 0-100 (0 = off, 100 = full brightness).
    """
    payload = {"method": "setPilot", "params": {"r": r, "g": g, "b": b, "transition": transition, "dimming": dimming}}
    send_udp(ip, payload)

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

def prompt_user_selection(lights: List[str], info: Dict[str, dict]) -> List[str]:
    """
    Show discovered lights and prompt the user to select which ones to control.
    Returns the list of selected IP addresses.
    """
    if not lights:
        print("No devices discovered.")
        return []
    
    print("\nDiscovered WIZ lights:")
    for i, ip in enumerate(lights):
        descr = info.get(ip, {})
        pretty = ip
        name = ""
        if isinstance(descr, dict):
            if "result" in descr and isinstance(descr["result"], dict):
                res = descr["result"]
                name = res.get("deviceName") or res.get("moduleName") or res.get("name") or res.get("alias") or ""
            else:
                name = descr.get("deviceName") or descr.get("moduleName") or ""
        if name:
            pretty += f" - {name}"
        print(f"  [{i}] {pretty}")

    sel = input("\nEnter comma-separated indices to select lights (or 'a' for all) [a]: ").strip()
    if sel.lower() in ("", "a", "all"):
        return lights
    chosen = []
    for chunk in sel.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            idx = int(chunk)
            if 0 <= idx < len(lights):
                chosen.append(lights[idx])
        except ValueError:
            pass
    return chosen

def change_bulb_selection(lights: List[str], info: Dict[str, dict], current: List[str]) -> List[str]:
    """
    Allow user to change the selected bulbs without rescanning.
    Returns new selection or current selection if cancelled.
    """
    print("\n=== Change Bulb Selection ===")
    print(f"Currently selected: {len(current)} bulb(s)")
    for ip in current:
        descr = info.get(ip, {})
        name = ""
        if isinstance(descr, dict):
            if "result" in descr and isinstance(descr["result"], dict):
                res = descr["result"]
                name = res.get("deviceName") or res.get("moduleName") or res.get("name") or res.get("alias") or ""
            else:
                name = descr.get("deviceName") or descr.get("moduleName") or ""
        print(f"  - {ip}" + (f" ({name})" if name else ""))
    
    print("\nAvailable lights:")
    for i, ip in enumerate(lights):
        descr = info.get(ip, {})
        pretty = ip
        name = ""
        if isinstance(descr, dict):
            if "result" in descr and isinstance(descr["result"], dict):
                res = descr["result"]
                name = res.get("deviceName") or res.get("moduleName") or res.get("name") or res.get("alias") or ""
            else:
                name = descr.get("deviceName") or descr.get("moduleName") or ""
        if name:
            pretty += f" - {name}"
        print(f"  [{i}] {pretty}")
    
    sel = input("\nEnter comma-separated indices (or 'a' for all, Enter to keep current): ").strip()
    if not sel:
        return current
    if sel.lower() in ("a", "all"):
        return lights
    chosen = []
    for chunk in sel.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            idx = int(chunk)
            if 0 <= idx < len(lights):
                chosen.append(lights[idx])
        except ValueError:
            pass
    return chosen if chosen else current

def choose_effect() -> str:
    """
    Display available effects menu and get user choice.
    Now organized by category for better usability.
    """
    print("\n" + "="*60)
    print("AVAILABLE EFFECTS".center(60))
    print("="*60)
    
    print("\n🌈 RAINBOW EFFECTS:")
    print("  rainbow_in_unison - all lights cycle colors together")
    print("  rainbow           - lights cycle colors with offsets")
    print("  party             - random colorful flashing")
    print("  fungi             - psychedelic funky animation")
    
    print("\n🎃 THEMED EFFECTS:")
    print("  spooky            - Halloween orange/purple flickers")
    print("  seasonal          - colors based on current season")
    print("  danger            - scary red strobe alarm")
    
    print("\n⛈️  NATURE EFFECTS:")
    print("  lightning         - stormy skies with lightning")
    print("  waterfall         - flowing blues and white")
    
    print("\n🎵 INTERACTIVE:")
    print("  reactive          - responds to microphone audio")
    print("  synth             - flash colors with number keys")
    
    print("\n⚙️  UTILITIES:")
    print("  white             - set to white color temperature")
    print("  rgba              - set custom RGBA color")
    
    print("\n📋 OPTIONS:")
    print("  change_bulbs      - select different bulbs")
    print("  rescan            - scan network for new bulbs")
    
    print("\n" + "="*60)
    
    choice = input("Choose effect [rainbow_in_unison]: ").strip().lower()
    
    # Map choices to effect names
    effect_map = {
        "rainbow_in_unison": "rainbow_in_unison",
        "rainbow": "rainbow",
        "spooky": "spooky",
        "white": "white",
        "rgba": "rgba",
        "party": "party",
        "synth": "synth",
        "reactive": "reactive",
        "seasonal": "seasonal",
        "danger": "danger",
        "lightning": "lightning",
        "waterfall": "waterfall",
        "fungi": "fungi",
        "change_bulbs": "change_bulbs",
        "rescan": "rescan",
    }
    
    # Allow partial matches for convenience
    if not choice:
        return "rainbow_in_unison"
    
    # Try exact match first
    if choice in effect_map:
        return effect_map[choice]
    
    # Try prefix matching
    matches = [name for name in effect_map.keys() if name.startswith(choice)]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        print(f"Ambiguous choice. Did you mean one of: {', '.join(matches)}?")
        return choose_effect()
    
    # No match found
    print(f"Unknown effect: {choice}. Please try again.")
    return choose_effect()

def get_kelvin_temperature() -> int:
    """
    Prompt user to enter a color temperature in Kelvin with guidance.
    Returns the validated temperature value.
    """
    print("\nEnter desired white temperature in Kelvin.")
    print("Common values:")
    print("  2700K - Warm white (incandescent bulb, cozy/relaxing)")
    print("  3000K - Soft white (warm, inviting)")
    print("  4000K - Neutral white (balanced, natural)")
    print("  5000K - Cool white (bright, energetic)")
    print("  6500K - Daylight (very bright, blue-ish)")
    
    while True:
        try:
            temp_str = input("Enter temperature in Kelvin [4000]: ").strip()
            if not temp_str:
                return 4000
            temp = int(temp_str)
            if temp < 1000 or temp > 10000:
                print("Please enter a value between 1000K and 10000K.")
                continue
            return temp
        except ValueError:
            print("Invalid input. Please enter a number.")

def run_rainbow_in_unison(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Cycle hue from 0 to 360; all lights show same hue at same time.
    duration: total seconds to run (None -> infinite until stop_event or Ctrl+C)
    stop_event: threading.Event to signal when to stop
    """
    print("Running rainbow_in_unison. Press Enter to stop or change mode.")
    t0 = time.time()
    hue = 0.0
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            r, g, b = hsv_to_rgb_255(hue, 1.0, 1.0)
            for ip in ips:
                set_color_rgb(ip, r, g, b)
            hue = (hue + 3.0) % 360
            time.sleep(SEND_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping effect.")

def run_rainbow(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Each light cycles through hues but with an offset so they aren't in unison.
    stop_event: threading.Event to signal when to stop
    """
    print("Running rainbow. Press Enter to stop or change mode.")
    t0 = time.time()
    base_hue = 0.0
    offsets = []
    n = len(ips)
    for i in range(n):
        offsets.append((i * (360.0 / max(1, n))) % 360)
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            for i, ip in enumerate(ips):
                hue = (base_hue + offsets[i]) % 360
                local_offset = (time.time() * 10.0 + i * 7) % 360
                hue = (hue + local_offset * 0.02) % 360
                r, g, b = hsv_to_rgb_255(hue, 1.0, 1.0)
                set_color_rgb(ip, r, g, b)
            base_hue = (base_hue + 2.0) % 360
            time.sleep(SEND_INTERVAL)
    except KeyboardInterrupt:
        print("\nStopping effect.")

def run_spooky(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Spooky effect: mostly orange/purple pulses with random flickers and occasional strobe.
    stop_event: threading.Event to signal when to stop
    """
    print("Running spooky. Press Enter to stop or change mode.")
    t0 = time.time()
    last_strobe = time.time()
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            now = time.time()
            # small chance to do a quick strobe across all lights
            if now - last_strobe > 6.0 and random.random() < 0.09:
                for flash in range(3):
                    for ip in ips:
                        set_color_rgb(ip, 255, 255, 255)
                    time.sleep(0.06)
                    for ip in ips:
                        set_color_rgb(ip, 0, 0, 0)
                    time.sleep(0.06)
                last_strobe = now
                continue

            for i, ip in enumerate(ips):
                base = "orange" if random.random() < 0.6 else "purple"
                if base == "orange":
                    hue = 30 + random.uniform(-8, 8)
                    sat = 0.9 + random.uniform(-0.1, 0.0)
                    val = 0.5 + random.uniform(-0.15, 0.25)
                else:
                    hue = 275 + random.uniform(-10, 10)
                    sat = 0.8 + random.uniform(-0.1, 0.1)
                    val = 0.3 + random.uniform(-0.12, 0.5)
                if random.random() < 0.08:
                    val = min(1.0, val + random.uniform(0.2, 0.6))
                r, g, b = hsv_to_rgb_255(hue, max(0.0, min(1.0, sat)), max(0.0, min(1.0, val)))
                r = int(max(0, min(255, r + random.randint(-8, 8))))
                g = int(max(0, min(255, g + random.randint(-8, 8))))
                b = int(max(0, min(255, b + random.randint(-8, 8))))
                set_color_rgb(ip, r, g, b)
            time.sleep(SEND_INTERVAL * 0.8)
    except KeyboardInterrupt:
        print("\nStopping effect.")

def run_white(ips: List[str], kelvin: int = 4000):
    """
    Set all lights to white at the specified color temperature in Kelvin.
    This is a one-time setting, not a continuous effect.
    """
    print(f"Setting lights to white at {kelvin}K...")
    r, g, b = kelvin_to_rgb_255(kelvin)
    for ip in ips:
        set_color_rgb(ip, r, g, b)
    print("Done.")

def get_rgba_input() -> Tuple[int, int, int, int]:
    """
    Prompt user to enter RGBA values.
    Returns (r, g, b, dimming) where r, g, b are 0-255 and dimming is 0-100.
    """
    print("\n=== RGBA Color Control ===")
    print("Enter color values:")
    
    while True:
        try:
            r = input("Red (0-255) [255]: ").strip()
            r = int(r) if r else 255
            if 0 <= r <= 255:
                break
            print("Please enter a value between 0 and 255.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    while True:
        try:
            g = input("Green (0-255) [255]: ").strip()
            g = int(g) if g else 255
            if 0 <= g <= 255:
                break
            print("Please enter a value between 0 and 255.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    while True:
        try:
            b = input("Blue (0-255) [255]: ").strip()
            b = int(b) if b else 255
            if 0 <= b <= 255:
                break
            print("Please enter a value between 0 and 255.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    while True:
        try:
            alpha = input("Dimming/Alpha (0-100, where 100=brightest) [100]: ").strip()
            alpha = int(alpha) if alpha else 100
            if 0 <= alpha <= 100:
                break
            print("Please enter a value between 0 and 100.")
        except ValueError:
            print("Invalid input. Please enter a number.")
    
    return r, g, b, alpha

def run_rgba(ips: List[str]):
    """
    Set all lights to a custom RGBA color with dimming control.
    This is a one-time setting, not a continuous effect.
    """
    r, g, b, dimming = get_rgba_input()
    print(f"Setting lights to RGB({r}, {g}, {b}) with {dimming}% brightness...")
    for ip in ips:
        set_color_rgb(ip, r, g, b, transition=0, dimming=dimming)
    print("Done.")

def run_party(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Party mode: random colorful flashing and pulsing.
    stop_event: threading.Event to signal when to stop
    """
    print("Running party mode. Press Enter to stop or change mode.")
    t0 = time.time()
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            # Random flash pattern
            pattern = random.choice(["all_same", "individual", "strobe"])
            
            if pattern == "all_same":
                # All lights same random color
                hue = random.uniform(0, 360)
                sat = random.uniform(0.7, 1.0)
                val = random.uniform(0.6, 1.0)
                r, g, b = hsv_to_rgb_255(hue, sat, val)
                for ip in ips:
                    set_color_rgb(ip, r, g, b)
                time.sleep(random.uniform(0.1, 0.4))
            
            elif pattern == "individual":
                # Each light different random color
                for ip in ips:
                    hue = random.uniform(0, 360)
                    sat = random.uniform(0.7, 1.0)
                    val = random.uniform(0.5, 1.0)
                    r, g, b = hsv_to_rgb_255(hue, sat, val)
                    set_color_rgb(ip, r, g, b)
                time.sleep(random.uniform(0.15, 0.5))
            
            elif pattern == "strobe":
                # Quick strobe
                for _ in range(random.randint(2, 5)):
                    hue = random.uniform(0, 360)
                    r, g, b = hsv_to_rgb_255(hue, 1.0, 1.0)
                    for ip in ips:
                        set_color_rgb(ip, r, g, b)
                    time.sleep(0.05)
                    for ip in ips:
                        set_color_rgb(ip, 0, 0, 0)
                    time.sleep(0.05)
                time.sleep(random.uniform(0.2, 0.6))
    
    except KeyboardInterrupt:
        print("\nStopping effect.")

def run_synth(ips: List[str], stop_event: threading.Event = None):
    """
    Synth mode: Flash bulbs using number keys 1-9 and 0.
    Each number key flashes a different color.
    stop_event: threading.Event to signal when to stop
    """
    print("\n=== Synth Mode ===")
    print("Press number keys 1-9 and 0 to flash different colors.")
    print("Press 'q' to quit synth mode.")
    
    # Color mapping for each key
    key_colors = {
        '1': (255, 0, 0),      # Red
        '2': (255, 127, 0),    # Orange
        '3': (255, 255, 0),    # Yellow
        '4': (0, 255, 0),      # Green
        '5': (0, 255, 255),    # Cyan
        '6': (0, 0, 255),      # Blue
        '7': (127, 0, 255),    # Purple
        '8': (255, 0, 255),    # Magenta
        '9': (255, 255, 255),  # White
        '0': (0, 0, 0),        # Black (off)
    }
    
    # Set terminal to non-blocking mode for key reading
    if sys.platform != 'win32':
        import tty
        import termios
        old_settings = termios.tcgetattr(sys.stdin)
        try:
            tty.setcbreak(sys.stdin.fileno())
            while True:
                if stop_event and stop_event.is_set():
                    break
                
                # Check if key is available
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    key = sys.stdin.read(1)
                    
                    if key.lower() == 'q':
                        break
                    
                    if key in key_colors:
                        r, g, b = key_colors[key]
                        for ip in ips:
                            set_color_rgb(ip, r, g, b)
                        print(f"Flash: {key} -> RGB({r}, {g}, {b})")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
    else:
        # Windows fallback - simpler input mode
        print("(Windows mode: type key and press Enter)")
        while True:
            if stop_event and stop_event.is_set():
                break
            try:
                key = input("Key (1-9, 0, q to quit): ").strip()
                if key.lower() == 'q':
                    break
                if key in key_colors:
                    r, g, b = key_colors[key]
                    for ip in ips:
                        set_color_rgb(ip, r, g, b)
                    print(f"Flash: {key} -> RGB({r}, {g}, {b})")
            except (EOFError, KeyboardInterrupt):
                break
    
    print("\nExiting synth mode.")


def run_reactive(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Reactive mode: Uses microphone to control lights based on audio levels.
    Requires PyAudio library.
    stop_event: threading.Event to signal when to stop
    """
    print("Running reactive mode. Press Enter to stop or change mode.")
    
    # Try to import PyAudio
    try:
        import pyaudio
        import numpy as np
    except ImportError:
        print("\nError: PyAudio not installed. Install with: pip install pyaudio")
        print("Falling back to simulated reactive mode...")
        time.sleep(2)
        # Fallback to simulated mode
        run_reactive_simulated(ips, stop_event, duration)
        return
    
    # Audio configuration
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 44100
    
    t0 = time.time()
    
    try:
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)
        
        print("Listening to microphone...")
        
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            try:
                # Read audio data
                data = stream.read(CHUNK, exception_on_overflow=False)
                audio_data = np.frombuffer(data, dtype=np.int16)
                
                # Calculate audio level (RMS)
                rms = np.sqrt(np.mean(audio_data**2))
                
                # Normalize to 0-1 range (adjust sensitivity)
                level = min(1.0, rms / 5000.0)
                
                # Map audio level to color (low = blue, high = red)
                hue = (1.0 - level) * 240  # 240 = blue, 0 = red
                sat = 0.9
                val = 0.3 + (level * 0.7)  # Brightness increases with volume
                
                r, g, b = hsv_to_rgb_255(hue, sat, val)
                
                for ip in ips:
                    set_color_rgb(ip, r, g, b)
                
                time.sleep(0.05)  # Small delay for responsiveness
                
            except Exception as e:
                print(f"Audio read error: {e}")
                break
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
    except Exception as e:
        print(f"Error initializing audio: {e}")
        print("Falling back to simulated mode...")
        run_reactive_simulated(ips, stop_event, duration)
    
    print("\nStopping reactive mode.")


def run_reactive_simulated(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Simulated reactive mode when PyAudio is not available.
    Creates a pulsing effect that simulates audio reactivity.
    """
    print("Running simulated reactive mode...")
    t0 = time.time()
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            # Simulate audio with sine wave
            elapsed = time.time() - t0
            level = (math.sin(elapsed * 3.0) + 1.0) / 2.0  # 0-1
            
            # Add some randomness
            level = level * random.uniform(0.7, 1.3)
            level = max(0.0, min(1.0, level))
            
            # Map to color
            hue = (1.0 - level) * 240
            sat = 0.9
            val = 0.3 + (level * 0.7)
            
            r, g, b = hsv_to_rgb_255(hue, sat, val)
            
            for ip in ips:
                set_color_rgb(ip, r, g, b)
            
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping effect.")


def run_seasonal(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Seasonal mode: Applies color schemes based on current date/season.
    - Winter (Dec-Feb): Cool blues and whites
    - Spring (Mar-May): Fresh greens and pastels
    - Summer (Jun-Aug): Bright yellows and warm colors
    - Fall (Sep-Nov): Orange, red, and brown tones
    stop_event: threading.Event to signal when to stop
    """
    print("Running seasonal mode. Press Enter to stop or change mode.")
    
    # Determine current season
    now = datetime.now()
    month = now.month
    
    if month in [12, 1, 2]:
        season = "winter"
        print(f"Current season: Winter")
        colors = [(180, 220, 255), (200, 230, 255), (150, 200, 255), (255, 255, 255)]
    elif month in [3, 4, 5]:
        season = "spring"
        print(f"Current season: Spring")
        colors = [(100, 255, 150), (150, 255, 200), (255, 200, 220), (200, 255, 255)]
    elif month in [6, 7, 8]:
        season = "summer"
        print(f"Current season: Summer")
        colors = [(255, 255, 100), (255, 200, 50), (255, 150, 50), (255, 100, 100)]
    else:  # Fall: Sep, Oct, Nov
        season = "fall"
        print(f"Current season: Fall")
        colors = [(255, 140, 0), (255, 100, 50), (200, 80, 40), (180, 50, 30)]
    
    t0 = time.time()
    color_index = 0
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            # Gradually transition through seasonal colors
            base_color = colors[color_index % len(colors)]
            
            # Add subtle variation
            r = max(0, min(255, base_color[0] + random.randint(-15, 15)))
            g = max(0, min(255, base_color[1] + random.randint(-15, 15)))
            b = max(0, min(255, base_color[2] + random.randint(-15, 15)))
            
            for ip in ips:
                set_color_rgb(ip, r, g, b)
            
            # Slow transition
            if random.random() < 0.05:
                color_index += 1
            
            time.sleep(SEND_INTERVAL * 3)
            
    except KeyboardInterrupt:
        print("\nStopping effect.")


def run_danger(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Danger mode: A scary red strobe effect.
    stop_event: threading.Event to signal when to stop
    """
    print("Running danger mode. Press Enter to stop or change mode.")
    t0 = time.time()
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            # Intense red strobe pattern
            pattern = random.choice(["fast_strobe", "slow_pulse", "flicker"])
            
            if pattern == "fast_strobe":
                # Rapid on/off
                for _ in range(random.randint(3, 8)):
                    for ip in ips:
                        set_color_rgb(ip, 255, 0, 0)
                    time.sleep(0.05)
                    for ip in ips:
                        set_color_rgb(ip, 0, 0, 0)
                    time.sleep(0.05)
                time.sleep(random.uniform(0.3, 0.8))
            
            elif pattern == "slow_pulse":
                # Pulsing red
                for intensity in range(0, 255, 20):
                    if stop_event and stop_event.is_set():
                        break
                    for ip in ips:
                        set_color_rgb(ip, intensity, 0, 0)
                    time.sleep(0.03)
                for intensity in range(255, 0, -20):
                    if stop_event and stop_event.is_set():
                        break
                    for ip in ips:
                        set_color_rgb(ip, intensity, 0, 0)
                    time.sleep(0.03)
            
            elif pattern == "flicker":
                # Erratic flickering
                for _ in range(random.randint(5, 15)):
                    r = random.randint(150, 255)
                    for ip in ips:
                        set_color_rgb(ip, r, 0, 0)
                    time.sleep(random.uniform(0.02, 0.1))
                
    except KeyboardInterrupt:
        print("\nStopping effect.")


def run_lightning(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Lightning mode: Stormy skies with random lightning flashes.
    stop_event: threading.Event to signal when to stop
    """
    print("Running lightning mode. Press Enter to stop or change mode.")
    t0 = time.time()
    last_lightning = time.time()
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            now = time.time()
            
            # Random lightning strikes
            if now - last_lightning > random.uniform(1.0, 5.0):
                # Lightning strike!
                strike_type = random.choice(["single", "double", "triple"])
                
                if strike_type == "single":
                    for ip in ips:
                        set_color_rgb(ip, 255, 255, 255)
                    time.sleep(random.uniform(0.03, 0.08))
                    for ip in ips:
                        set_color_rgb(ip, 30, 30, 50)
                
                elif strike_type == "double":
                    for _ in range(2):
                        for ip in ips:
                            set_color_rgb(ip, 255, 255, 255)
                        time.sleep(random.uniform(0.02, 0.05))
                        for ip in ips:
                            set_color_rgb(ip, 30, 30, 50)
                        time.sleep(random.uniform(0.1, 0.2))
                
                else:  # triple
                    for _ in range(3):
                        brightness = random.randint(200, 255)
                        for ip in ips:
                            set_color_rgb(ip, brightness, brightness, brightness)
                        time.sleep(random.uniform(0.02, 0.04))
                        for ip in ips:
                            set_color_rgb(ip, 30, 30, 50)
                        time.sleep(random.uniform(0.05, 0.15))
                
                last_lightning = now
            else:
                # Dark stormy sky between lightning
                r = random.randint(25, 40)
                g = random.randint(25, 40)
                b = random.randint(40, 60)
                for ip in ips:
                    set_color_rgb(ip, r, g, b)
                time.sleep(SEND_INTERVAL * 2)
                
    except KeyboardInterrupt:
        print("\nStopping effect.")


def run_waterfall(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Waterfall mode: Turbulent blues and white flowing effect.
    stop_event: threading.Event to signal when to stop
    """
    print("Running waterfall mode. Press Enter to stop or change mode.")
    t0 = time.time()
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            # Create flowing water effect
            for i, ip in enumerate(ips):
                # Use time and position to create wave effect
                elapsed = time.time() - t0
                wave = math.sin(elapsed * 2.0 + i * 0.5) * 0.5 + 0.5
                
                # Mix between deep blue and white
                if random.random() < 0.15:
                    # White foam
                    r = random.randint(200, 255)
                    g = random.randint(220, 255)
                    b = random.randint(240, 255)
                else:
                    # Blue water with varying intensity
                    base_blue = int(wave * 100 + 100)
                    r = random.randint(0, 30)
                    g = random.randint(40, 100)
                    b = random.randint(base_blue, min(255, base_blue + 80))
                
                set_color_rgb(ip, r, g, b)
            
            time.sleep(SEND_INTERVAL * 0.8)
            
    except KeyboardInterrupt:
        print("\nStopping effect.")


def run_fungi(ips: List[str], stop_event: threading.Event = None, duration=None):
    """
    Fungi mode: A fun and funky psychedelic animation.
    stop_event: threading.Event to signal when to stop
    """
    print("Running fungi mode. Press Enter to stop or change mode.")
    t0 = time.time()
    
    try:
        while True:
            if stop_event and stop_event.is_set():
                break
            if duration and (time.time() - t0) >= duration:
                break
            
            elapsed = time.time() - t0
            
            # Create psychedelic patterns
            for i, ip in enumerate(ips):
                # Multiple overlapping waves create trippy effect
                wave1 = math.sin(elapsed * 1.5 + i * 0.8)
                wave2 = math.cos(elapsed * 2.3 + i * 1.2)
                wave3 = math.sin(elapsed * 0.7 + i * 0.5)
                
                # Map waves to hue (full spectrum)
                hue = ((wave1 + wave2 + wave3) * 60 + elapsed * 30 + i * 40) % 360
                
                # High saturation and varying brightness for psychedelic effect
                sat = 0.8 + wave1 * 0.2
                val = 0.6 + wave2 * 0.3
                
                r, g, b = hsv_to_rgb_255(hue, max(0.0, min(1.0, sat)), max(0.0, min(1.0, val)))
                
                # Add occasional sparkle
                if random.random() < 0.05:
                    r = min(255, r + random.randint(50, 100))
                    g = min(255, g + random.randint(50, 100))
                    b = min(255, b + random.randint(50, 100))
                
                set_color_rgb(ip, r, g, b)
            
            time.sleep(SEND_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nStopping effect.")


def main():
    config = load_config()
    base_ip = config.get("base_ip", "192.168.1")
    
    # Try to load from cache first
    discovered = load_cache()
    if discovered:
        print(f"Loaded {len(discovered)} bulb(s) from cache.")
        print("Use 'rescan' option to refresh the bulb list.")
    else:
        print(f"Scanning {base_ip}.0-255 (no broadcast) for WIZ devices...")
        discovered = scan_ip_range(base_ip=base_ip, start=0, end=255, workers=80)
        if discovered:
            save_cache(discovered)
            print(f"Found {len(discovered)} bulb(s). Cached for future use.")
    
    ips = sorted(discovered.keys())
    selected = prompt_user_selection(ips, discovered)
    if not selected:
        print("No lights selected. Exiting.")
        return

    # Interactive mode loop
    stop_event = threading.Event()
    effect_thread = None
    
    while True:
        # Stop any running effect
        if effect_thread and effect_thread.is_alive():
            stop_event.set()
            effect_thread.join(timeout=2.0)
        
        # Reset stop event for next effect
        stop_event.clear()
        
        # Choose effect
        effect = choose_effect()
        
        # Handle rescan
        if effect == "rescan":
            print(f"\nRescanning {base_ip}.0-255 for WIZ devices...")
            discovered = scan_ip_range(base_ip=base_ip, start=0, end=255, workers=80)
            if discovered:
                save_cache(discovered)
                print(f"Found {len(discovered)} bulb(s). Cache updated.")
            else:
                print("No bulbs found during rescan.")
            ips = sorted(discovered.keys())
            # Re-select if current selection is invalid
            selected = [ip for ip in selected if ip in ips]
            if not selected:
                selected = prompt_user_selection(ips, discovered)
                if not selected:
                    print("No lights selected. Exiting.")
                    return
            continue
        
        # Handle change bulbs
        if effect == "change_bulbs":
            selected = change_bulb_selection(ips, discovered, selected)
            if not selected:
                print("No lights selected. Exiting.")
                return
            continue
        
        # Handle one-time effects
        if effect == "white":
            kelvin = get_kelvin_temperature()
            run_white(selected, kelvin)
            print("\nPress Enter to change mode or Ctrl+C to exit.")
            try:
                input()
            except KeyboardInterrupt:
                print("\nExiting.")
                break
        
        elif effect == "rgba":
            run_rgba(selected)
            print("\nPress Enter to change mode or Ctrl+C to exit.")
            try:
                input()
            except KeyboardInterrupt:
                print("\nExiting.")
                break
        
        elif effect == "synth":
            # Synth mode handles its own input
            run_synth(selected, stop_event)
        
        # Handle continuous effects
        elif effect in ["rainbow_in_unison", "rainbow", "spooky", "party", "reactive", "seasonal", "danger", "lightning", "waterfall", "fungi"]:
            # Run effect in background thread
            if effect == "rainbow_in_unison":
                effect_thread = threading.Thread(target=run_rainbow_in_unison, args=(selected, stop_event))
            elif effect == "rainbow":
                effect_thread = threading.Thread(target=run_rainbow, args=(selected, stop_event))
            elif effect == "spooky":
                effect_thread = threading.Thread(target=run_spooky, args=(selected, stop_event))
            elif effect == "party":
                effect_thread = threading.Thread(target=run_party, args=(selected, stop_event))
            elif effect == "reactive":
                effect_thread = threading.Thread(target=run_reactive, args=(selected, stop_event))
            elif effect == "seasonal":
                effect_thread = threading.Thread(target=run_seasonal, args=(selected, stop_event))
            elif effect == "danger":
                effect_thread = threading.Thread(target=run_danger, args=(selected, stop_event))
            elif effect == "lightning":
                effect_thread = threading.Thread(target=run_lightning, args=(selected, stop_event))
            elif effect == "waterfall":
                effect_thread = threading.Thread(target=run_waterfall, args=(selected, stop_event))
            elif effect == "fungi":
                effect_thread = threading.Thread(target=run_fungi, args=(selected, stop_event))
            
            effect_thread.daemon = True
            effect_thread.start()
            
            # Wait for user to press Enter to change mode
            try:
                input()
            except KeyboardInterrupt:
                print("\nExiting.")
                stop_event.set()
                if effect_thread:
                    effect_thread.join(timeout=2.0)
                break
        else:
            print("Unknown effect. Exiting.")
            break

if __name__ == "__main__":
    main()
