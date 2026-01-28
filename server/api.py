from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import sys
import json
import requests

from flask import Flask, jsonify, request, send_file, make_response
from flask_cors import CORS

# ============================================================================
# IMPORT GLOBAL CONFIGURATION
# ============================================================================
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as global_config

# ============================================================================
# GLOBAL VARIABLES AND CACHES
# ============================================================================
_FLOOD_ROADS_CACHE: Dict[str, Dict[str, Any]] = {}  # key -> geojson dict

# ============================================================================
# SETUP FLASK APP
# ============================================================================
PROJECT_ROOT = global_config.PROJECT_ROOT
WEB_DIR = global_config.WEB_DIR

app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")

# ============================================================================
# CORS CONFIGURATION - FIXED
# ============================================================================
if global_config.CORS_ENABLED:
    cors_config = {
        "origins": global_config.CORS_ORIGINS if global_config.CORS_ORIGINS != ["*"] else "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
    CORS(app, resources={r"/api/*": cors_config})
    print(f"[CORS] Enabled with origins: {global_config.CORS_ORIGINS}")
else:
    print("[CORS] Disabled")

# ============================================================================
# ROUTING IMPORT
# ============================================================================
try:
    from server.routing import find_route, get_graph_info, precompute_all_flood_data, get_cache_stats
except ImportError:
    from routing import find_route, get_graph_info, precompute_all_flood_data, get_cache_stats

# Import cache functions for API exposure
try:
    from server.routing import save_route_cache_to_disk, invalidate_caches
except ImportError:
    from routing import save_route_cache_to_disk, invalidate_caches

# ============================================================================
# USE GLOBAL CONFIGURATION
# ============================================================================
TOMTOM_API_KEY = global_config.TOMTOM_API_KEY
GEOPANDAS_OK = global_config.GEOPANDAS_OK
gpd = global_config.gpd
shape = global_config.shape

FLOOD_DIR = global_config.FLOOD_GEOCODED_DIR
STATIC_FLOOD = global_config.STATIC_FLOOD_PATH
ROAD_CANDIDATES = global_config.ROADS_CANDIDATES
TRAFFIC_DIRS = global_config.TRAFFIC_DIRS
TRAFFIC_SNAPSHOTS_DIR = global_config.TRAFFIC_SNAPSHOTS_DIR

# Print configuration summary
global_config.print_config_summary()

# Import modular handlers
from server.handlers.flood_handler import (
    list_flood_files,
    resolve_flood_path_by_index,
    get_flood_data,
    get_flooded_roads
)
from server.handlers.traffic_handler import (
    get_traffic_snapshot,
    get_traffic_info
)


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
        result = get_flood_data(time_param)
        if result["success"]:
            return result["data"], 200, {"Content-Type": "application/json"}
        return jsonify({"error": "Failed to retrieve flood data"}), 500
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
    if not global_config.GEOPANDAS_OK:
        return jsonify({"error": "geopandas/shapely not available. Install geopandas to use /api/flood-roads"}), 500

    try:
        time_param = request.args.get("time")
        result = get_flooded_roads(time_param)
        
        # Add cache headers for 1 hour - flood data for a specific time doesn't change
        response = make_response(jsonify(result))
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/traffic")
def api_traffic():
    """
    Returns traffic snapshot JSON.
    GET /api/traffic?time=<flood_index> - syncs with flood timeline
    GET /api/traffic?timestamp=<ISO_timestamp> - finds nearest snapshot
    """
    time_param = request.args.get("time")
    timestamp_param = request.args.get("timestamp")
    
    nearest = get_traffic_snapshot(time_param, timestamp_param)
    
    if nearest and nearest.exists():
        return send_file(str(nearest), mimetype="application/json")
    
    return jsonify({"error": "No traffic snapshot available"}), 404


@app.route("/api/traffic/info")
def api_traffic_info():
    """
    Returns info about which traffic snapshot matches the given flood time index.
    """
    time_param = request.args.get("time")
    result = get_traffic_info(time_param)
    return jsonify(result)


@app.route("/api/traffic/refresh", methods=["POST"])
def api_traffic_refresh():
    """Endpoint for collector to refresh traffic data."""
    return jsonify({
        "status": "ok",
        "message": "Refresh endpoint is ready. Hook it to your collector script when you want live updates."
    })


# ----------------------------
# TomTom proxies
# ----------------------------
@app.route("/api/tomtom/geocode")
def api_tomtom_geocode():
    """Proxy TomTom geocoding endpoint."""
    search_query = request.args.get("search", "").strip()
    if not search_query:
        return jsonify({"error": "Missing 'search' parameter"}), 400
    if not TOMTOM_API_KEY:
        return jsonify({"error": "TOMTOM_API_KEY is not set on server"}), 500

    url = f"https://api.tomtom.com/search/2/geocode/{search_query}.json"
    try:
        resp = requests.get(url, params={"key": TOMTOM_API_KEY}, timeout=12)
        resp.raise_for_status()
        return jsonify(resp.json())
    except Exception as e:
        return jsonify({"error": f"TomTom geocode failed: {str(e)}"}), 500


@app.route("/api/tomtom/traffic-tiles/<int:z>/<int:x>/<int:y>")
def api_tomtom_traffic_tiles(z: int, x: int, y: int):
    """Proxy TomTom traffic tiles endpoint."""
    if not TOMTOM_API_KEY:
        return jsonify({"error": "TOMTOM_API_KEY is not set on server"}), 500

    url = f"https://api.tomtom.com/traffic/map/4/tile/flow/relative0/{z}/{x}/{y}.png"
    try:
        resp = requests.get(url, params={"key": TOMTOM_API_KEY}, timeout=12)
        resp.raise_for_status()

        response = make_response(resp.content)
        response.headers["Content-Type"] = "image/png"
        response.headers["Cache-Control"] = "public, max-age=3600"
        return response
    except Exception as e:
        return jsonify({"error": f"Traffic tiles proxy failed: {str(e)}"}), 500


# ----------------------------
# ROUTING ENDPOINTS
# ----------------------------
@app.route("/api/route")
def api_route():
    """
    Calculate optimal route based on parameters.
    
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

        # Validate route type
        allowed = {"shortest", "fastest", "flood_avoid", "smart"}
        if route_type not in allowed:
            route_type = "shortest"

        # Calculate route
        geojson = find_route(origin_lat, origin_lon, dest_lat, dest_lon, route_type, flood_time=flood_time)

        if isinstance(geojson, dict):
            geojson.setdefault("properties", {})
            geojson["properties"]["flood_time"] = flood_time
            geojson["properties"]["route_type"] = route_type

        if geojson.get("error"):
            return jsonify(geojson), 404

        return jsonify(geojson)

    except TypeError:
        # Backward compatibility if find_route() doesn't accept flood_time
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
    """Get information about the underlying graph."""
    return jsonify(get_graph_info())


@app.route("/api/cache-stats")
def api_cache_stats():
    """Return progressive route cache statistics."""
    return jsonify(get_cache_stats())


@app.route("/api/debug/dump-cache")
def api_debug_dump_cache():
    """
    Dumps the current in-memory route cache to a JSON file in web/data.
    This allows manual inspection of cached routes.
    """
    try:
        # Save to web/data so it's easily accessible/visible
        output_dir = WEB_DIR / "data"
        saved_path = dump_route_cache_to_disk(output_dir)
        filename = Path(saved_path).name
        
        return jsonify({
            "status": "success",
            "message": f"Cache dumped to {filename}",
            "file_path": saved_path,
            "url": f"/data/{filename}"  # Since web is static folder
        })
    except Exception as e:
        return jsonify({"error": f"Failed to dump cache: {str(e)}"}), 500


# ----------------------------
# STATIC FILE SERVING
# ----------------------------
@app.route("/")
def index():
    """Serve the main HTML page."""
    return app.send_static_file("index.html")


# ----------------------------
# BACKGROUND INITIALIZATION
# ----------------------------
import threading


def _init_background_cache():
    """Start flood data pre-computation in background thread."""
    def background_cache():
        print("\n[Background] Starting flood data pre-computation...")
        try:
            precompute_all_flood_data()
            print("[Background] ✓ Flood cache ready!\n")
        except Exception as e:
            print(f"[Background] Warning: Flood pre-computation failed: {e}\n")
    
    # Start caching in background (daemon thread won't block app startup)
    cache_thread = threading.Thread(target=background_cache, daemon=True)
    cache_thread.start()
    print("[Background] Cache initialization started in background thread")


# Start background caching when app module loads
_init_background_cache()


if __name__ == "__main__":
    print("\n" + "="*70)
    print("[Flask Server] Starting on development server...")
    print("="*70)
    print(f"Host: {global_config.FLASK_HOST}:{global_config.FLASK_PORT}")
    print("Note: First route calculations may be slower while cache builds")
    print("Press Ctrl+C to stop\n")
    
    app.run(
        host=global_config.FLASK_HOST,
        port=global_config.FLASK_PORT,
        debug=global_config.FLASK_DEBUG
    )

