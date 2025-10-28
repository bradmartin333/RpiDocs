"""
Configuration and cache management for WIZ lights.
"""
import json
import os
from typing import Dict, Optional

# File paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(SCRIPT_DIR, "wiz_bulb_cache.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")


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
