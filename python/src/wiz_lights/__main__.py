"""
Main entry point for WIZ lights control application.
"""
import threading
from .config import load_config, save_cache, load_cache
from .network import scan_ip_range
from .ui import prompt_user_selection, change_bulb_selection, choose_effect, choose_effect_tui, get_kelvin_temperature, get_rgba_input
from .controls import (
    run_rainbow_in_unison, run_rainbow, run_spooky, run_white, run_rgba, 
    run_party, run_synth, run_reactive, run_seasonal, run_danger,
    run_lightning, run_waterfall, run_fungi
)


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
            r, g, b, dimming = get_rgba_input()
            run_rgba(selected, r, g, b, dimming)
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


if __name__ == '__main__':
    main()
