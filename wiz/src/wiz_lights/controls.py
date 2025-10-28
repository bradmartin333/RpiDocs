"""
Control modes for WIZ lights.

Each control mode is a function that controls the lights in a specific way.
"""
import time
import random
import math
import sys
import select
import threading
from datetime import datetime
from typing import List
from .colors import hsv_to_rgb_255, kelvin_to_rgb_255
from .network import set_color_rgb

# Constants
SEND_INTERVAL = 0.12  # seconds between color updates

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

def run_rgba(ips: List[str], r: int, g: int, b: int, dimming: int):
    """
    Set all lights to a custom RGBA color with dimming control.
    This is a one-time setting, not a continuous effect.
    """
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
    
    # Try to import PyAudio and numpy
    try:
        import pyaudio
        import numpy as np
    except ImportError as e:
        missing = str(e).split("'")[1] if "'" in str(e) else "PyAudio or NumPy"
        print(f"\nError: {missing} not installed.")
        print("Install with: uv sync --extra audio")
        print("Or on Debian/Ubuntu: sudo apt install portaudio19-dev && uv sync --extra audio")
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
