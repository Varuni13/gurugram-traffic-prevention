from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

from flask import Flask, jsonify, request, send_file, make_response
from flask_cors import CORS
import os
import json
import requests

# Optional (needed for flood->roads intersection)
try:
    import geopandas as gpd
    from shapely.geometry import shape
    GEOPANDAS_OK = True
except Exception:
    gpd = None
    shape = None
    GEOPANDAS_OK = False

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)
    print(f"[Config] Loaded .env from: {env_path}")
except Exception:
    print("[Config] dotenv not loaded (ok). Using system env only.")

# Routing import (your existing backend routing module)
try:
    from server.routing import find_route, get_graph_info
except Exception:
    from routing import find_route, get_graph_info


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")
CORS(app)

TOMTOM_KEY = os.getenv("TOMTOM_API_KEY", "").strip()
if not TOMTOM_KEY:
    print("[WARNING] TOMTOM_API_KEY not set. TomTom proxy endpoints will fail until you set it.")

# ----------------------------
# FLOOD DATA (GeoJSON timeline)
# ----------------------------
FLOOD_DIR = WEB_DIR / "data" / "GEOCODED"   # DYYYYMMDDHHMM.geojson
STATIC_FLOOD = WEB_DIR / "data" / "flood_roads.geojson"  # optional

# ----------------------------
# ROADS (for flood->road intersection)
# ----------------------------
ROAD_CANDIDATES = [
    WEB_DIR / "data" / "clean_roads.geojson",
    WEB_DIR / "data" / "roads_clean.geojson",
    WEB_DIR / "data" / "roads.geojson",
    WEB_DIR / "data" / "clean_road.geojson",
]

# ----------------------------
# TRAFFIC SNAPSHOTS (JSON)
# ----------------------------
TRAFFIC_DIRS = [
    WEB_DIR / "data",
    PROJECT_ROOT / "collector" / "outputs",
]

print("=" * 70)
print("[Flask Server Starting]")
print(f"Web dir:         {WEB_DIR}")
print(f"Flood dir:       {FLOOD_DIR} | exists={FLOOD_DIR.exists()}")
print(f"Static flood:    {STATIC_FLOOD} | exists={STATIC_FLOOD.exists()}")
print(f"GeoPandas:       {GEOPANDAS_OK}")
print("=" * 70)


def _parse_ts_from_name(filename: str) -> Optional[datetime]:
    """
    DYYYYMMDDHHMM.geojson -> datetime
    """
    try:
        stem = Path(filename).stem
        if not stem.startswith("D"):
            return None
        s = stem[1:13]  # YYYYMMDDHHMM
        return datetime.strptime(s, "%Y%m%d%H%M")
    except Exception:
        return None


def _label_from_name(filename: str) -> str:
    ts = _parse_ts_from_name(filename)
    if ts:
        return ts.strftime("%Y-%m-%d %H:%M")
    return filename


def _find_roads_file() -> Optional[Path]:
    for p in ROAD_CANDIDATES:
        if p.exists():
            return p
    return None


def list_flood_files(start_dt: Optional[datetime] = None, end_dt: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Returns time-series flood files only (no static flood).
    [{\"index\": 0, \"filename\": \"...\", \"label\": \"...\", \"timestamp\": \"...\"}]
    Index is continuous for slider use.
    """
    out: List[Dict[str, Any]] = []

    if FLOOD_DIR.exists():
        files = sorted(FLOOD_DIR.glob("D*.geojson"))

        # Filter by time window if provided
        filtered = []
        for f in files:
            ts = _parse_ts_from_name(f.name)
            if ts is None:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue
            filtered.append((ts, f))

        # Start from index 0 (no static flood offset)
        for i, (ts, f) in enumerate(filtered):
            out.append({
                "index": i,
                "filename": f.name,
                "label": ts.strftime("%Y-%m-%d %H:%M"),
                "timestamp": ts.isoformat()
            })

    return out


def _resolve_flood_path_by_index(time_param: Optional[str]) -> Path:
    """
    time_param can be:
      - None => first available
      - an index integer => match list_flood_files index
      - a filename => match directly
    """
    files = list_flood_files()
    if not files:
        raise FileNotFoundError("No flood files found in web/data/GEOCODED")

    target = files[0]

    if time_param is not None:
        try:
            idx = int(time_param)
            match = next((x for x in files if x["index"] == idx), None)
            if not match:
                raise FileNotFoundError(f"Flood time index not found: {idx}")
            target = match
        except ValueError:
            match = next((x for x in files if x["filename"] == time_param), None)
            if not match:
                raise FileNotFoundError(f"Flood time not found: {time_param}")
            target = match

    # All flood files are in FLOOD_DIR (no static flood anymore)
    path = FLOOD_DIR / target["filename"]

    if not path.exists():
        raise FileNotFoundError(f"Flood file missing on disk: {path}")

    return path, target.get("timestamp")  # Also return timestamp for traffic sync


@app.route("/api/times")
def api_times():
    """
    Optional filters:
      /api/times?start=2025-07-13T11:30&end=2025-07-13T18:17
    """
    start = request.args.get("start")
    end = request.args.get("end")

    start_dt = None
    end_dt = None

    try:
        if start:
            start_dt = datetime.fromisoformat(start)
        if end:
            end_dt = datetime.fromisoformat(end)
    except Exception:
        return jsonify({"error": "Invalid start/end. Use ISO like 2025-07-13T11:30"}), 400

    files = list_flood_files(start_dt=start_dt, end_dt=end_dt)
    return jsonify({"count": len(files), "files": files})


@app.route("/api/flood")
def api_flood():
    """
    Returns flood polygons GeoJSON (as stored).
    GET /api/flood?time=<index or filename>
    """
    try:
        time_param = request.args.get("time")
        path, _ = _resolve_flood_path_by_index(time_param)

        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed reading flood GeoJSON: {str(e)}"}), 500


@app.route("/api/flood-roads")
def api_flood_roads():
    """
    Returns flooded ROAD SEGMENTS (LineString) by intersecting:
      roads_clean.geojson  ∩  flood polygons at selected time

    GET /api/flood-roads?time=<index or filename>
    """
    if not GEOPANDAS_OK:
        return jsonify({"error": "geopandas/shapely not available. Install geopandas to use /api/flood-roads"}), 500

    roads_path = _find_roads_file()
    if not roads_path:
        return jsonify({"error": "Road GeoJSON not found. Put clean_roads.geojson into web/data/"}), 404

    try:
        time_param = request.args.get("time")
        flood_path, _ = _resolve_flood_path_by_index(time_param)

        roads = gpd.read_file(roads_path)
        flood = gpd.read_file(flood_path)

        if roads.empty:
            return jsonify({"type": "FeatureCollection", "features": [], "properties": {"note": "roads empty"}})

        if flood.empty:
            return jsonify({"type": "FeatureCollection", "features": [], "properties": {"note": "flood empty"}})

        # Ensure CRS compatibility (many geojsons are EPSG:4326)
        if roads.crs is None:
            roads = roads.set_crs("EPSG:4326")
        if flood.crs is None:
            flood = flood.set_crs("EPSG:4326")
        if roads.crs != flood.crs:
            flood = flood.to_crs(roads.crs)

        # Keep only polygon geometries from flood
        flood = flood[flood.geometry.notnull()]
        roads = roads[roads.geometry.notnull()]

        # Fast spatial join: roads that intersect any flood polygon
        flood_poly = flood[~flood.geometry.is_empty].copy()
        roads_ln = roads[~roads.geometry.is_empty].copy()

        # Detect depth column in flood data
        depth_col = None
        for col in ["depth", "flood_depth", "water_depth", "wd"]:
            if col in flood_poly.columns:
                depth_col = col
                break
        
        # Prepare flood polygons for join - include depth if available
        flood_cols = ["geometry"]
        if depth_col:
            flood_cols.append(depth_col)
        
        # geopandas sjoin uses spatial index
        joined = gpd.sjoin(roads_ln, flood_poly[flood_cols], how="inner", predicate="intersects")

        if joined.empty:
            return jsonify({
                "type": "FeatureCollection",
                "features": [],
                "properties": {"roads_file": roads_path.name, "flood_file": flood_path.name, "count": 0}
            })

        # Deduplicate - keep the maximum depth for each road if multiple flood polygons
        if depth_col and depth_col in joined.columns:
            # Group by road and get max depth
            joined = joined.groupby(joined.index).agg({
                "geometry": "first",
                depth_col: "max",
                **{c: "first" for c in joined.columns if c not in ["geometry", depth_col, "index_right"]}
            }).reset_index(drop=True)
            joined = gpd.GeoDataFrame(joined, geometry="geometry", crs=roads.crs)
            
            # Add flood status based on depth threshold (0.3m)
            DEPTH_THRESHOLD = 0.3
            joined["flood_depth"] = joined[depth_col].fillna(0)
            joined["is_passable"] = joined["flood_depth"] <= DEPTH_THRESHOLD
            joined["flood_status"] = joined.apply(
                lambda r: "passable" if r["flood_depth"] <= DEPTH_THRESHOLD else "dangerous", 
                axis=1
            )
        else:
            # No depth info - mark all as unknown/dangerous (conservative)
            joined = joined.drop_duplicates()
            joined["flood_depth"] = None
            joined["is_passable"] = False
            joined["flood_status"] = "unknown"

        # Add a flag
        joined["flooded"] = True

        out = json.loads(joined.to_json())
        out.setdefault("properties", {})
        out["properties"].update({
            "roads_file": roads_path.name,
            "flood_file": flood_path.name,
            "count": len(out.get("features", [])),
            "depth_column": depth_col,
            "passable_count": int(joined["is_passable"].sum()) if "is_passable" in joined.columns else 0,
            "dangerous_count": int((~joined["is_passable"]).sum()) if "is_passable" in joined.columns else len(joined)
        })
        return jsonify(out)

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed flood->roads intersection: {str(e)}"}), 500


# Traffic snapshot directory
TRAFFIC_SNAPSHOTS_DIR = PROJECT_ROOT / "collector" / "outputs" / "traffic_snapshots"


def _find_nearest_traffic_snapshot(target_timestamp: Optional[str]) -> Optional[Path]:
    """
    Find traffic snapshot closest to the target timestamp by TIME-OF-DAY only.
    This allows matching flood times (July) to traffic data (January).
    Traffic files: traffic_YYYY-MM-DDTHH-MM-SS.json
    
    Returns: (snapshot_path, info_dict)
    """
    if not TRAFFIC_SNAPSHOTS_DIR.exists():
        return None
    
    snapshots = list(TRAFFIC_SNAPSHOTS_DIR.glob("traffic_*.json"))
    if not snapshots:
        return None
    
    if not target_timestamp:
        # Return most recent
        return max(snapshots, key=lambda p: p.stat().st_mtime)
    
    # Parse target timestamp to get TIME-OF-DAY only (flood timestamps are in IST)
    try:
        target_dt = datetime.fromisoformat(target_timestamp)
        target_minutes = target_dt.hour * 60 + target_dt.minute  # Minutes since midnight (IST)
    except:
        return max(snapshots, key=lambda p: p.stat().st_mtime)
    
    # Parse all traffic snapshot times and CONVERT UTC TO IST
    traffic_times = []  # [(path, minutes_since_midnight_IST, datetime)]
    for snap in snapshots:
        try:
            ts_str = snap.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
            ts_str = ts_str[:19]
            ts_str = ts_str.replace(":", "-", 2)
            snap_dt = datetime.fromisoformat(ts_str)
            
            # Convert UTC to IST (add 5 hours 30 minutes)
            utc_minutes = snap_dt.hour * 60 + snap_dt.minute
            ist_minutes = (utc_minutes + 330) % (24 * 60)  # 330 = 5*60 + 30
            
            traffic_times.append((snap, ist_minutes, snap_dt))
        except:
            continue
    
    if not traffic_times:
        return max(snapshots, key=lambda p: p.stat().st_mtime)
    
    # Find nearest by time-of-day in IST (ignoring date)
    best_match = None
    best_diff = float('inf')
    
    for snap, snap_ist_minutes, snap_dt in traffic_times:
        diff = abs(snap_ist_minutes - target_minutes)
        if diff < best_diff:
            best_diff = diff
            best_match = snap
    
    return best_match if best_match else max(snapshots, key=lambda p: p.stat().st_mtime)


@app.route("/api/traffic")
def api_traffic():
    """
    Returns traffic snapshot JSON.
    GET /api/traffic?time=<flood_index> - syncs with flood timeline
    GET /api/traffic?timestamp=<ISO_timestamp> - finds nearest snapshot
    """
    time_param = request.args.get("time")
    timestamp_param = request.args.get("timestamp")
    
    # If time (flood index) provided, get flood timestamp and find matching traffic
    if time_param:
        try:
            files = list_flood_files()
            idx = int(time_param)
            flood_file = next((x for x in files if x["index"] == idx), None)
            if flood_file and flood_file.get("timestamp"):
                timestamp_param = flood_file["timestamp"]
        except:
            pass
    
    # Try to find nearest traffic snapshot
    nearest = _find_nearest_traffic_snapshot(timestamp_param)
    if nearest and nearest.exists():
        return send_file(str(nearest), mimetype="application/json")
    
    # Fallback to latest_traffic.json
    for d in TRAFFIC_DIRS:
        if not d.exists():
            continue
        candidate = d / "latest_traffic.json"
        if candidate.exists():
            return send_file(str(candidate), mimetype="application/json")

    return jsonify({"error": "No traffic snapshot available"}), 404


@app.route("/api/traffic/info")
def api_traffic_info():
    """
    Returns metadata about which traffic snapshot is being used for a given flood time.
    GET /api/traffic/info?time=<flood_index>
    """
    time_param = request.args.get("time")
    timestamp_param = None
    flood_timestamp = None
    
    # If time (flood index) provided, get flood timestamp
    if time_param:
        try:
            files = list_flood_files()
            idx = int(time_param)
            flood_file = next((x for x in files if x["index"] == idx), None)
            if flood_file and flood_file.get("timestamp"):
                timestamp_param = flood_file["timestamp"]
                flood_timestamp = flood_file["timestamp"]
        except:
            pass
    
    # Find nearest traffic snapshot
    nearest = _find_nearest_traffic_snapshot(timestamp_param)
    
    if nearest and nearest.exists():
        # Parse traffic time from filename
        try:
            ts_str = nearest.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
            ts_str = ts_str[:19]
            ts_str = ts_str.replace(":", "-", 2)
            snap_dt = datetime.fromisoformat(ts_str)
            # Convert to IST (UTC+5:30)
            ist_hour = (snap_dt.hour + 5) % 24
            ist_minute = snap_dt.minute + 30
            if ist_minute >= 60:
                ist_minute -= 60
                ist_hour = (ist_hour + 1) % 24
            traffic_time_ist = f"{ist_hour:02d}:{ist_minute:02d}"
            
            return jsonify({
                "traffic_file": nearest.name,
                "traffic_time_ist": traffic_time_ist,
                "flood_timestamp": flood_timestamp,
                "flood_index": int(time_param) if time_param else None,
                "matched": True
            })
        except:
            pass
    
    return jsonify({
        "traffic_file": None,
        "traffic_time_ist": "N/A",
        "flood_timestamp": flood_timestamp,
        "matched": False
    })


@app.route("/api/traffic/refresh", methods=["POST"])
def api_traffic_refresh():
    return jsonify({
        "status": "ok",
        "message": "Refresh endpoint is ready. Hook it to your collector script when you want live updates."
    })


# ----------------------------
# TomTom proxies
# ----------------------------
@app.route("/api/tomtom/geocode")

def api_tomtom_geocode():
    search_query = request.args.get("search", "").strip()
    if not search_query:
        return jsonify({"error": "Missing 'search' parameter"}), 400
    if not TOMTOM_KEY:
        return jsonify({"error": "TOMTOM_API_KEY is not set on server"}), 500

    # Force search within Gurugram to avoid flying to Hyderabad etc.
    # We append " Gurugram" if not present, and restrict to India
    if "gurugram" not in search_query.lower() and "gurgaon" not in search_query.lower():
        search_query += " Gurugram"
        
    url = f"https://api.tomtom.com/search/2/geocode/{search_query}.json"
    params = {
        "key": TOMTOM_KEY,
        "countrySet": "IN",
        "limit": 5,
        "lat": 28.4595,  # Biasing towards Gurugram center
        "lon": 77.0266,
        "radius": 20000  # 20km radius bias
    }
    
    try:
        resp = requests.get(url, params=params, timeout=12)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"TomTom geocode failed: {str(e)}"}), 500


@app.route("/api/tomtom/traffic-tiles/<int:z>/<int:x>/<int:y>")
def api_tomtom_traffic_tiles(z: int, x: int, y: int):
    if not TOMTOM_KEY:
        return jsonify({"error": "TOMTOM_API_KEY is not set on server"}), 500

    url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png"
    try:
        resp = requests.get(url, params={"key": TOMTOM_KEY}, timeout=12)
        resp.raise_for_status()

        response = make_response(resp.content)
        response.headers["Content-Type"] = "image/png"
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    except Exception as e:
        return jsonify({"error": f"Traffic tiles proxy failed: {str(e)}"}), 500


# ----------------------------
# Routing
# ----------------------------
@app.route("/api/route")
def api_route():
    """
    Query params:
      origin_lat, origin_lon, dest_lat, dest_lon
      type: shortest | fastest | flood_avoid | smart
      flood_time: selected flood index from slider
    """
    try:
        origin_lat = request.args.get("origin_lat")
        origin_lon = request.args.get("origin_lon")
        dest_lat = request.args.get("dest_lat")
        dest_lon = request.args.get("dest_lon")
        route_type = request.args.get("type", "shortest").strip().lower()
        flood_time = request.args.get("flood_time", None)

        if not all([origin_lat, origin_lon, dest_lat, dest_lon]):
            return jsonify({"error": "Missing required parameters"}), 400

        try:
            origin_lat = float(origin_lat)
            origin_lon = float(origin_lon)
            dest_lat = float(dest_lat)
            dest_lon = float(dest_lon)
        except ValueError:
            return jsonify({"error": "Coordinates must be valid numbers"}), 400

        # Let routing module decide how to handle these; fallback to shortest if unknown
        allowed = {"shortest", "fastest", "flood_avoid", "smart"}
        if route_type not in allowed:
            route_type = "shortest"

        # IMPORTANT: pass flood_time too (your routing can use it)
        geojson = find_route(origin_lat, origin_lon, dest_lat, dest_lon, route_type, flood_time=flood_time)

        if isinstance(geojson, dict):
            geojson.setdefault("properties", {})
            geojson["properties"]["flood_time"] = flood_time
            geojson["properties"]["route_type"] = route_type

        if geojson.get("error"):
            return jsonify(geojson), 404

        return jsonify(geojson)

    except TypeError:
        # Backward compatibility if your find_route() does not accept flood_time
        try:
            geojson = find_route(origin_lat, origin_lon, dest_lat, dest_lon, route_type)
            if isinstance(geojson, dict):
                geojson.setdefault("properties", {})
                geojson["properties"]["flood_time"] = flood_time
                geojson["properties"]["route_type"] = route_type
            return jsonify(geojson)
        except Exception as e:
            return jsonify({"error": f"Route calculation failed: {str(e)}"}), 500

    except Exception as e:
        return jsonify({"error": f"Route calculation failed: {str(e)}"}), 500


@app.route("/api/graph-info")
def api_graph_info():
    return jsonify(get_graph_info())


@app.route("/")
def index():
    return app.send_static_file("index.html")


if __name__ == "__main__":
    print("\n[Starting Flask] Access at http://localhost:8000")
    print("Press Ctrl+C to stop\n")
    app.run(host="0.0.0.0", port=8000, debug=False)
