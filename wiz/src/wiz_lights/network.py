"""
Network discovery and communication for WIZ lights.
"""
import socket
import json
import concurrent.futures
from typing import Dict

# WIZ bulb communication constants
WIZ_PORT = 38899
PROBE_TIMEOUT = 0.35  # seconds to wait for a single probe response

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
