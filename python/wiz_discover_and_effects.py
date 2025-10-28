#!/usr/bin/env python3
"""
wiz_discover_and_effects.py

Discover WIZ lights on the local network by probing 192.168.1.0-255 (no broadcasts)
and provide simple effects:
 - rainbow_in_unison: all lights cycle through HSV colors in sync
 - rainbow: lights cycle through HSV colors with different offsets (not in unison)
 - spooky: a Halloween-ish effect (orange/purple flicker/pulse with occasional strobe)
 - white: reset lights to white at a specified color temperature in Kelvin

Usage:
    python3 wiz_discover_and_effects.py

Notes:
 - This script probes each IP in the 192.168.1.* /24 range (no UDP broadcast).
 - Probing is done by sending a small JSON query to UDP port 38899 and waiting
   briefly for a response. This is slower than broadcast discovery but avoids
   sending broadcast packets as requested.
 - Effects run in the background and can be changed by pressing Enter (no need for Ctrl+C).
 - Press Ctrl+C to exit the program completely.
"""

import socket
import json
import time
import colorsys
import random
import concurrent.futures
import threading
import math
from typing import Dict, List, Tuple

WIZ_PORT = 38899
PROBE_TIMEOUT = 0.35   # seconds to wait for a single probe response
SEND_INTERVAL = 0.12   # seconds between color updates (tweak for speed/CPU)

# A lightweight query that many WIZ bulbs will answer to
PROBE_PAYLOAD = {"method": "getPilot", "params": {}}

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

def scan_192_168_1_range(start: int = 0, end: int = 255, workers: int = 60) -> Dict[str, dict]:
    """
    Scan the IPv4 range 192.168.1.start .. 192.168.1.end (inclusive) by probing each IP.
    Returns a dict mapping IP -> response dict for each responsive device.
    """
    prefix = "192.168.1."
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

def set_color_rgb(ip: str, r: int, g: int, b: int, transition: int = 0) -> None:
    """
    Tell a WIZ light to set color using RGB values (0-255).
    Uses method 'setPilot' which is commonly supported by WIZ lights.
    transition is transition time in milliseconds (device dependent).
    """
    payload = {"method": "setPilot", "params": {"r": r, "g": g, "b": b, "transition": transition, "dimming": 100}}
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
    if not lights:
        print("No devices discovered.")
        return []

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

def choose_effect() -> str:
    print("\nAvailable effects:")
    print("  1) rainbow_in_unison  - all lights cycle through the same hues together")
    print("  2) rainbow            - lights cycle through hues with offsets (not in unison)")
    print("  3) spooky             - Halloween effect (orange/purple flicker and strobes)")
    print("  4) white              - reset to white at a specified temperature in Kelvin")
    choice = input("Choose effect [1]: ").strip()
    if choice in ("2", "rainbow"):
        return "rainbow"
    if choice in ("3", "spooky"):
        return "spooky"
    if choice in ("4", "white"):
        return "white"
    return "rainbow_in_unison"

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

def main():
    print("Scanning 192.168.1.0-255 (no broadcast) for WIZ devices...")
    discovered = scan_192_168_1_range(start=0, end=255, workers=80)
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
        
        if effect == "white":
            kelvin = get_kelvin_temperature()
            run_white(selected, kelvin)
            print("\nPress Enter to change mode or Ctrl+C to exit.")
            try:
                input()
            except KeyboardInterrupt:
                print("\nExiting.")
                break
        elif effect in ["rainbow_in_unison", "rainbow", "spooky"]:
            # Run effect in background thread
            if effect == "rainbow_in_unison":
                effect_thread = threading.Thread(target=run_rainbow_in_unison, args=(selected, stop_event))
            elif effect == "rainbow":
                effect_thread = threading.Thread(target=run_rainbow, args=(selected, stop_event))
            elif effect == "spooky":
                effect_thread = threading.Thread(target=run_spooky, args=(selected, stop_event))
            
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
