"""
User interface functions for WIZ lights.

Includes menu display, TUI, and user interaction functions.
"""
import sys
from typing import Dict, List, Tuple
from .colors import kelvin_to_rgb_255


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

def choose_effect_tui() -> str:
    """
    Interactive TUI for selecting controls using arrow keys.
    Falls back to simple input on Windows or if curses unavailable.
    """
    # Define all controls with categories
    controls = [
        ("🌈 RAINBOW CONTROLS", [
            ("rainbow_in_unison", "all lights cycle colors together"),
            ("rainbow", "lights cycle colors with offsets"),
            ("party", "random colorful flashing"),
            ("fungi", "psychedelic funky animation"),
        ]),
        ("🎃 THEMED CONTROLS", [
            ("spooky", "Halloween orange/purple flickers"),
            ("seasonal", "colors based on current season"),
            ("danger", "scary red strobe alarm"),
        ]),
        ("⛈️  NATURE CONTROLS", [
            ("lightning", "stormy skies with lightning"),
            ("waterfall", "flowing blues and white"),
        ]),
        ("🎵 INTERACTIVE", [
            ("reactive", "responds to microphone audio"),
            ("synth", "flash colors with number keys"),
        ]),
        ("⚙️  UTILITIES", [
            ("white", "set to white color temperature"),
            ("rgba", "set custom RGBA color"),
        ]),
        ("📋 OPTIONS", [
            ("change_bulbs", "select different bulbs"),
            ("rescan", "scan network for new bulbs"),
        ]),
    ]
    
    # Flatten controls list for navigation
    flat_controls = []
    for category, items in controls:
        for name, desc in items:
            flat_controls.append((name, desc, category))
    
    # Try to use curses for interactive selection
    if sys.platform != 'win32':
        try:
            import curses
            
            def draw_menu(stdscr, selected_idx):
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                
                # Title
                title = "INTERACTIVE CONTROL SELECTOR"
                stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
                stdscr.addstr(1, 0, "="*width)
                
                # Instructions
                instructions = "Use ↑/↓ arrows to navigate, Enter to select, 'q' to cancel"
                stdscr.addstr(2, (width - len(instructions)) // 2, instructions)
                stdscr.addstr(3, 0, "="*width)
                
                # Display controls
                current_category = None
                row = 4
                
                for idx, (name, desc, category) in enumerate(flat_controls):
                    if row >= height - 2:
                        break
                    
                    # Show category header if changed
                    if category != current_category:
                        if row < height - 2:
                            stdscr.addstr(row, 0, f"\n{category}")
                            row += 2
                            current_category = category
                    
                    if row >= height - 2:
                        break
                    
                    # Highlight selected item
                    if idx == selected_idx:
                        stdscr.addstr(row, 2, f"→ {name}", curses.A_REVERSE)
                        stdscr.addstr(row, 4 + len(name), f" - {desc}", curses.A_REVERSE)
                    else:
                        stdscr.addstr(row, 2, f"  {name}")
                        stdscr.addstr(row, 4 + len(name), f" - {desc}")
                    
                    row += 1
                
                stdscr.refresh()
            
            def select_with_curses(stdscr):
                curses.curs_set(0)  # Hide cursor
                selected_idx = 0
                
                while True:
                    draw_menu(stdscr, selected_idx)
                    key = stdscr.getch()
                    
                    if key == curses.KEY_UP and selected_idx > 0:
                        selected_idx -= 1
                    elif key == curses.KEY_DOWN and selected_idx < len(flat_controls) - 1:
                        selected_idx += 1
                    elif key == ord('\n') or key == curses.KEY_ENTER:
                        return flat_controls[selected_idx][0]
                    elif key == ord('q') or key == ord('Q'):
                        return "rainbow_in_unison"  # Default
            
            result = curses.wrapper(select_with_curses)
            return result
            
        except Exception as e:
            print(f"TUI unavailable ({e}), using numbered menu...")
    
    # Fallback to numbered menu
    print("\n" + "="*60)
    print("INTERACTIVE CONTROL SELECTOR".center(60))
    print("="*60)
    
    for idx, (name, desc, category) in enumerate(flat_controls):
        print(f"  {idx+1:2d}) {name:20s} - {desc}")
    
    print("\n" + "="*60)
    
    while True:
        try:
            choice = input(f"Select control (1-{len(flat_controls)}) [1]: ").strip()
            if not choice:
                return flat_controls[0][0]
            
            idx = int(choice) - 1
            if 0 <= idx < len(flat_controls):
                return flat_controls[idx][0]
            else:
                print(f"Please enter a number between 1 and {len(flat_controls)}")
        except ValueError:
            print("Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            return "rainbow_in_unison"

def choose_effect() -> str:
    """
    Display available controls menu and get user choice.
    Now organized by category for better usability.
    """
    print("\n" + "="*60)
    print("AVAILABLE CONTROLS".center(60))
    print("="*60)
    
    print("\n🌈 RAINBOW CONTROLS:")
    print("  rainbow_in_unison - all lights cycle colors together")
    print("  rainbow           - lights cycle colors with offsets")
    print("  party             - random colorful flashing")
    print("  fungi             - psychedelic funky animation")
    
    print("\n🎃 THEMED CONTROLS:")
    print("  spooky            - Halloween orange/purple flickers")
    print("  seasonal          - colors based on current season")
    print("  danger            - scary red strobe alarm")
    
    print("\n⛈️  NATURE CONTROLS:")
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
    print("Type 'tui' for interactive menu or enter control name")
    
    choice = input("Choose control [rainbow_in_unison]: ").strip().lower()
    
    # Check if user wants TUI
    if choice == "tui":
        return choose_effect_tui()
    
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
        print(f"Ambiguous choice '{choice}'. Matches: {', '.join(matches)}")
        print("Please use a more specific name.")
        # Return first match as fallback instead of recursing
        return matches[0]
    
    # No match found - return default instead of recursing
    print(f"Unknown effect: '{choice}'. Using default (rainbow_in_unison).")
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

def choose_effect_tui() -> str:
    """
    Interactive TUI for selecting controls using arrow keys.
    Falls back to simple input on Windows or if curses unavailable.
    """
    # Define all controls with categories
    controls = [
        ("🌈 RAINBOW CONTROLS", [
            ("rainbow_in_unison", "all lights cycle colors together"),
            ("rainbow", "lights cycle colors with offsets"),
            ("party", "random colorful flashing"),
            ("fungi", "psychedelic funky animation"),
        ]),
        ("🎃 THEMED CONTROLS", [
            ("spooky", "Halloween orange/purple flickers"),
            ("seasonal", "colors based on current season"),
            ("danger", "scary red strobe alarm"),
        ]),
        ("⛈️  NATURE CONTROLS", [
            ("lightning", "stormy skies with lightning"),
            ("waterfall", "flowing blues and white"),
        ]),
        ("🎵 INTERACTIVE", [
            ("reactive", "responds to microphone audio"),
            ("synth", "flash colors with number keys"),
        ]),
        ("⚙️  UTILITIES", [
            ("white", "set to white color temperature"),
            ("rgba", "set custom RGBA color"),
        ]),
        ("📋 OPTIONS", [
            ("change_bulbs", "select different bulbs"),
            ("rescan", "scan network for new bulbs"),
        ]),
    ]
    
    # Flatten controls list for navigation
    flat_controls = []
    for category, items in controls:
        for name, desc in items:
            flat_controls.append((name, desc, category))
    
    # Try to use curses for interactive selection
    if sys.platform != 'win32':
        try:
            import curses
            
            def draw_menu(stdscr, selected_idx):
                stdscr.clear()
                height, width = stdscr.getmaxyx()
                
                # Title
                title = "INTERACTIVE CONTROL SELECTOR"
                stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
                stdscr.addstr(1, 0, "="*width)
                
                # Instructions
                instructions = "Use ↑/↓ arrows to navigate, Enter to select, 'q' to cancel"
                stdscr.addstr(2, (width - len(instructions)) // 2, instructions)
                stdscr.addstr(3, 0, "="*width)
                
                # Display controls
                current_category = None
                row = 4
                
                for idx, (name, desc, category) in enumerate(flat_controls):
                    if row >= height - 2:
                        break
                    
                    # Show category header if changed
                    if category != current_category:
                        if row < height - 2:
                            stdscr.addstr(row, 0, f"\n{category}")
                            row += 2
                            current_category = category
                    
                    if row >= height - 2:
                        break
                    
                    # Highlight selected item
                    if idx == selected_idx:
                        stdscr.addstr(row, 2, f"→ {name}", curses.A_REVERSE)
                        stdscr.addstr(row, 4 + len(name), f" - {desc}", curses.A_REVERSE)
                    else:
                        stdscr.addstr(row, 2, f"  {name}")
                        stdscr.addstr(row, 4 + len(name), f" - {desc}")
                    
                    row += 1
                
                stdscr.refresh()
            
            def select_with_curses(stdscr):
                curses.curs_set(0)  # Hide cursor
                selected_idx = 0
                
                while True:
                    draw_menu(stdscr, selected_idx)
                    key = stdscr.getch()
                    
                    if key == curses.KEY_UP and selected_idx > 0:
                        selected_idx -= 1
                    elif key == curses.KEY_DOWN and selected_idx < len(flat_controls) - 1:
                        selected_idx += 1
                    elif key == ord('\n') or key == curses.KEY_ENTER:
                        return flat_controls[selected_idx][0]
                    elif key == ord('q') or key == ord('Q'):
                        return "rainbow_in_unison"  # Default
            
            result = curses.wrapper(select_with_curses)
            return result
            
        except Exception as e:
            print(f"TUI unavailable ({e}), using numbered menu...")
    
    # Fallback to numbered menu
    print("\n" + "="*60)
    print("INTERACTIVE CONTROL SELECTOR".center(60))
    print("="*60)
    
    for idx, (name, desc, category) in enumerate(flat_controls):
        print(f"  {idx+1:2d}) {name:20s} - {desc}")
    
    print("\n" + "="*60)
    
    while True:
        try:
            choice = input(f"Select control (1-{len(flat_controls)}) [1]: ").strip()
            if not choice:
                return flat_controls[0][0]
            
            idx = int(choice) - 1
            if 0 <= idx < len(flat_controls):
                return flat_controls[idx][0]
            else:
                print(f"Please enter a number between 1 and {len(flat_controls)}")
        except ValueError:
            print("Please enter a valid number")
        except (EOFError, KeyboardInterrupt):
            return "rainbow_in_unison"

def choose_effect() -> str:
    """
    Display available controls menu and get user choice.
    Now organized by category for better usability.
    """
    print("\n" + "="*60)
    print("AVAILABLE CONTROLS".center(60))
    print("="*60)
    
    print("\n🌈 RAINBOW CONTROLS:")
    print("  rainbow_in_unison - all lights cycle colors together")
    print("  rainbow           - lights cycle colors with offsets")
    print("  party             - random colorful flashing")
    print("  fungi             - psychedelic funky animation")
    
    print("\n🎃 THEMED CONTROLS:")
    print("  spooky            - Halloween orange/purple flickers")
    print("  seasonal          - colors based on current season")
    print("  danger            - scary red strobe alarm")
    
    print("\n⛈️  NATURE CONTROLS:")
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
    print("Type 'tui' for interactive menu or enter control name")
    
    choice = input("Choose control [rainbow_in_unison]: ").strip().lower()
    
    # Check if user wants TUI
    if choice == "tui":
        return choose_effect_tui()
    
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
        print(f"Ambiguous choice '{choice}'. Matches: {', '.join(matches)}")
        print("Please use a more specific name.")
        # Return first match as fallback instead of recursing
        return matches[0]
    
    # No match found - return default instead of recursing
    print(f"Unknown effect: '{choice}'. Using default (rainbow_in_unison).")
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
