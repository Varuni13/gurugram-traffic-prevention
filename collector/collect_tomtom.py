# collector/collect_tomtom.py
import csv
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

from config import TOMTOM_API_KEY, MONITOR_POINTS


# ----------------------------
# Helpers
# ----------------------------
def atomic_write_json(path: Path, payload: dict) -> None:
    """
    Write JSON safely: write temp -> replace.
    Prevents UI from reading half-written JSON.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def fetch_flow_segment(lat: float, lon: float) -> dict:
    """
    One monitoring point = one TomTom API request.
    """
    base = "https://api.tomtom.com/traffic/services/4/flowSegmentData/relative0/10/json"
    params = {"point": f"{lat},{lon}", "key": TOMTOM_API_KEY}

    r = requests.get(base, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    fsd = data.get("flowSegmentData", {})
    if not fsd:
        raise RuntimeError("No flowSegmentData in TomTom response")

    current_speed = fsd.get("currentSpeed")
    free_flow_speed = fsd.get("freeFlowSpeed")
    current_tt = fsd.get("currentTravelTime")
    free_flow_tt = fsd.get("freeFlowTravelTime")
    confidence = fsd.get("confidence")
    frc = fsd.get("frc")

    delay_s = None
    if isinstance(current_tt, (int, float)) and isinstance(free_flow_tt, (int, float)):
        delay_s = current_tt - free_flow_tt

    speed_ratio = None
    if (
        isinstance(current_speed, (int, float))
        and isinstance(free_flow_speed, (int, float))
        and free_flow_speed
        and free_flow_speed != 0
    ):
        speed_ratio = current_speed / free_flow_speed

    return {
        "currentSpeed_kmph": current_speed,
        "freeFlowSpeed_kmph": free_flow_speed,
        "currentTravelTime_s": current_tt,
        "freeFlowTravelTime_s": free_flow_tt,
        "delay_s": delay_s,
        "speed_ratio": speed_ratio,
        "confidence": confidence,
        "frc": frc,
    }


# ----------------------------
# Main
# ----------------------------
def main():
    if not TOMTOM_API_KEY or "PASTE" in TOMTOM_API_KEY:
        raise SystemExit("Please set TOMTOM_API_KEY in collector/config.py")

    root = Path(__file__).resolve().parents[1]  # project root
    out_dir = root / "collector" / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)

    web_data_dir = root / "web" / "data"
    web_data_dir.mkdir(parents=True, exist_ok=True)

    # timestamps
    # Define IST timezone explicitly (fixes server timezone issues)
    IST = timezone(timedelta(hours=5, minutes=30))

    ts_utc = datetime.now(timezone.utc).isoformat()
    ts_local = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S") + " IST"

    results = []
    total = len(MONITOR_POINTS)

    print(f"Collecting TomTom traffic snapshot for {total} points…")

    for i, p in enumerate(MONITOR_POINTS, start=1):
        lat, lon = p["lat"], p["lon"]
        name = p.get("name", f"point_{i}")

        try:
            row = fetch_flow_segment(lat, lon)
            row.update(
                {
                    "name": name,
                    "query_lat": lat,
                    "query_lon": lon,
                    "timestamp_utc": ts_utc,
                    "timestamp_local": ts_local,  # ✅ readable for UI popups
                }
            )
            results.append(row)
            print(f"  [{i}/{total}] OK: {name} speed={row.get('currentSpeed_kmph')} km/h")
        except Exception as e:
            print(f"  [{i}/{total}] FAIL: {name} -> {e}")

        time.sleep(0.15)  # be polite

    snapshot = {
        "generated_at_utc": ts_utc,
        "generated_at_local": ts_local,
        "count": len(results),
        "points": results,
    }

    # 1) latest snapshot (collector)
    latest_json = out_dir / "latest_traffic.json"
    atomic_write_json(latest_json, snapshot)
    print(f"Wrote {latest_json}")

    # 2) latest snapshot (web)
    web_json = web_data_dir / "latest_traffic.json"
    atomic_write_json(web_json, snapshot)
    print(f"Copied to {web_json}")

    # 3) timestamped snapshot (optional history for future slider)
    snap_dir = out_dir / "traffic_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    safe_ts = ts_utc.replace(":", "-")  # Windows-safe
    snap_path = snap_dir / f"traffic_{safe_ts}.json"
    atomic_write_json(snap_path, snapshot)
    print(f"Wrote snapshot {snap_path}")

    # 4) CSV history
    csv_path = out_dir / "traffic_flow_history.csv"
    fieldnames = [
        "timestamp_utc",
        "timestamp_local",
        "name",
        "query_lat",
        "query_lon",
        "frc",
        "currentSpeed_kmph",
        "freeFlowSpeed_kmph",
        "currentTravelTime_s",
        "freeFlowTravelTime_s",
        "delay_s",
        "speed_ratio",
        "confidence",
    ]

    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            w.writeheader()
        for r in results:
            w.writerow({k: r.get(k) for k in fieldnames})

    print(f"Appended {len(results)} rows to {csv_path}")
    print("Done.")


if __name__ == "__main__":
    main()
