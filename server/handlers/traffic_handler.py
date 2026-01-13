# server/handlers/traffic_handler.py
"""
Traffic data endpoint handlers.
Handles traffic snapshots and TomTom proxy endpoints.
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

# Import global config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config as global_config


def find_nearest_traffic_snapshot(target_timestamp: Optional[str]) -> Optional[Path]:
    """
    Find traffic snapshot closest to target timestamp.
    Traffic files: traffic_YYYY-MM-DDTHH-MM-SS.json
    
    Args:
        target_timestamp: ISO format timestamp
        
    Returns:
        Path to nearest traffic snapshot or None
    """
    traffic_dir = global_config.TRAFFIC_SNAPSHOTS_DIR
    
    if not traffic_dir.exists():
        return None
    
    snapshots = list(traffic_dir.glob("traffic_*.json"))
    if not snapshots:
        return None
    
    if not target_timestamp:
        # Return most recent
        return max(snapshots, key=lambda p: p.stat().st_mtime)
    
    # Parse target timestamp
    try:
        target_dt = datetime.fromisoformat(target_timestamp)
    except Exception:
        return max(snapshots, key=lambda p: p.stat().st_mtime)
    
    # Find nearest by parsing filename timestamps
    best_match = None
    best_diff = float('inf')
    
    for snap in snapshots:
        try:
            # Parse timestamp from filename: traffic_2026-01-08T12-47-09.828164+00-00.json
            ts_str = snap.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
            ts_str = ts_str[:19]  # Take YYYY:MM:DDTHH:MM:SS
            ts_str = ts_str.replace(":", "-", 2)  # Back to YYYY-MM-DDTHH:MM:SS
            snap_dt = datetime.fromisoformat(ts_str)
            diff = abs((snap_dt - target_dt).total_seconds())
            if diff < best_diff:
                best_diff = diff
                best_match = snap
        except Exception:
            continue
    
    return best_match if best_match else max(snapshots, key=lambda p: p.stat().st_mtime)


def get_traffic_snapshot(time_param: Optional[str] = None, timestamp_param: Optional[str] = None) -> Optional[Path]:
    """
    Get traffic snapshot file path.
    
    Args:
        time_param: Flood time index
        timestamp_param: ISO timestamp
        
    Returns:
        Path to traffic file or None
    """
    # If flood time index provided, convert to timestamp
    if time_param:
        try:
            from server.handlers.flood_handler import list_flood_files
            files = list_flood_files()
            idx = int(time_param)
            flood_file = next((x for x in files if x["index"] == idx), None)
            if flood_file and flood_file.get("timestamp"):
                timestamp_param = flood_file["timestamp"]
        except Exception:
            pass
    
    # Find nearest snapshot
    nearest = find_nearest_traffic_snapshot(timestamp_param)
    if nearest and nearest.exists():
        return nearest
    
    # Fallback to latest_traffic.json
    for d in global_config.TRAFFIC_DIRS:
        if not d.exists():
            continue
        candidate = d / "latest_traffic.json"
        if candidate.exists():
            return candidate

    return None


def get_traffic_info(time_param: Optional[str] = None) -> dict:
    """
    Get information about traffic snapshot matching flood time.
    
    Args:
        time_param: Flood time index
        
    Returns:
        Dictionary with traffic matching info
    """
    # Resolve flood time
    flood_ts = None
    try:
        from server.handlers.flood_handler import list_flood_files
        files = list_flood_files()
        if files:
            idx = int(time_param) if time_param is not None else 0
            match = next((x for x in files if x["index"] == idx), None)
            if match and match.get("timestamp"):
                flood_ts = match["timestamp"]
    except Exception:
        pass

    # Find nearest traffic
    nearest = find_nearest_traffic_snapshot(flood_ts)
    
    if nearest and nearest.exists():
        ts_str = "N/A"
        try:
            raw = nearest.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
            raw = raw[:19].replace(":", "-", 2)
            dt = datetime.fromisoformat(raw)
            # Convert to IST for display (UTC+5:30)
            dt_ist = dt + timedelta(hours=5, minutes=30)
            ts_str = dt_ist.strftime("%H:%M")
        except Exception:
            ts_str = nearest.name

        lag = 0.0
        if flood_ts:
            try:
                ft = datetime.fromisoformat(flood_ts)
                raw = nearest.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
                raw = raw[:19].replace(":", "-", 2)
                nt = datetime.fromisoformat(raw)
                lag = (nt - ft).total_seconds()
            except Exception:
                pass

        return {
            "matched": True,
            "traffic_file": nearest.name,
            "traffic_time_ist": ts_str,
            "lag_seconds": round(lag, 1)
        }

    return {
        "matched": False,
        "traffic_file": None,
        "traffic_time_ist": None,
        "lag_seconds": None
    }
