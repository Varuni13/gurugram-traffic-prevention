# Global configuration for Traffic Forecasting Emulator
"""
Centralized configuration for the entire application.
This module should be imported by all components.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ============================================================================
# PROJECT STRUCTURE
# ============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent
WEB_DIR = PROJECT_ROOT / "web"
COLLECTOR_DIR = PROJECT_ROOT / "collector"
COLLECTOR_OUTPUTS = COLLECTOR_DIR / "outputs"
SERVER_DIR = PROJECT_ROOT / "server"

# ============================================================================
# DATA PATHS
# ============================================================================
# Flood data paths
FLOOD_GEOCODED_DIR = WEB_DIR / "data" / "GEOCODED"
STATIC_FLOOD_PATH = WEB_DIR / "data" / "flood_roads.geojson"

# Roads data paths
ROADS_CANDIDATES = [
    WEB_DIR / "data" / "clean_roads.geojson",
    WEB_DIR / "data" / "roads_clean.geojson",
    WEB_DIR / "data" / "roads.geojson",
    WEB_DIR / "data" / "clean_road.geojson",
    COLLECTOR_OUTPUTS / "clean_roads.geojson",
]

# Graph data paths
GRAPH_CANDIDATES = [
    WEB_DIR / "data" / "ggn_extent.graphml",
    PROJECT_ROOT / "ggn_extent.graphml",
    COLLECTOR_OUTPUTS / "ggn_extent.graphml",
]

# Traffic data paths
TRAFFIC_DIRS = [
    WEB_DIR / "data",
    COLLECTOR_OUTPUTS,
]

TRAFFIC_SNAPSHOTS_DIR = COLLECTOR_OUTPUTS / "traffic_snapshots"
LATEST_TRAFFIC_PATH = WEB_DIR / "data" / "latest_traffic.json"

# ============================================================================
# SERVER CONFIGURATION
# ============================================================================
# Flask app config
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")  # Bind to all interfaces for network access
FLASK_PORT = int(os.getenv("FLASK_PORT", "9110"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# CORS configuration
CORS_ENABLED = os.getenv("CORS_ENABLED", "True").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS]

# ============================================================================
# API KEYS AND CREDENTIALS
# ============================================================================
# Load environment variables from .env if available
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[Config] Loaded environment from: {env_path}")

TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "").strip()

if not TOMTOM_API_KEY:
    print("[WARNING] TOMTOM_API_KEY not set. TomTom endpoints will fail until configured.")

# ============================================================================
# COLLECTOR CONFIGURATION
# ============================================================================
# Monitoring points for traffic collection
MONITOR_POINTS = [
    {"name": "IFFCO Chowk", "lat": 28.4726, "lon": 77.0726},
    {"name": "MG Road", "lat": 28.4795, "lon": 77.0806},
    {"name": "Cyber Hub", "lat": 28.4947, "lon": 77.0897},
    {"name": "Golf Course Rd", "lat": 28.4503, "lon": 77.0972},
    {"name": "Sohna Road", "lat": 28.4073, "lon": 77.0460},
    {"name": "NH-48 (Ambience)", "lat": 28.5052, "lon": 77.0970},
    {"name": "Rajiv Chowk", "lat": 28.4691, "lon": 77.0366},
    {"name": "Huda City Centre", "lat": 28.4595, "lon": 77.0722},
    {"name": "Sector 56", "lat": 28.4244, "lon": 77.1070},
    {"name": "Manesar Rd", "lat": 28.3540, "lon": 76.9440},
]

COLLECTOR_INTERVAL_MIN = int(os.getenv("COLLECTOR_INTERVAL_MIN", "10"))

# ============================================================================
# ROUTING CONFIGURATION
# ============================================================================
# Flood depth threshold for obstacle detection
FLOOD_DEPTH_THRESHOLD_M = float(os.getenv("FLOOD_DEPTH_THRESHOLD_M", "0.3"))
FLOOD_PENALTY = float(os.getenv("FLOOD_PENALTY", "1000000.0"))

# Route cache settings
MAX_ROUTE_CACHE_SIZE = int(os.getenv("MAX_ROUTE_CACHE_SIZE", "500"))

# ============================================================================
# GEOPANDAS AND SPATIAL LIBRARIES
# ============================================================================
try:
    import geopandas as gpd
    from shapely.geometry import shape, LineString
    GEOPANDAS_OK = True
except ImportError:
    gpd = None
    shape = None
    LineString = None
    GEOPANDAS_OK = False

try:
    import osmnx as ox
    OSMNX_AVAILABLE = True
except ImportError:
    ox = None
    OSMNX_AVAILABLE = False

# ============================================================================
# WEB APP CONFIGURATION
# ============================================================================
# Frontend configuration - times for filtering
TIMES_START = os.getenv("TIMES_START", "2025-07-13T11:25")
TIMES_END = os.getenv("TIMES_END", "2025-07-13T18:17")

# Preset locations for web UI
PRESET_LOCATIONS = {
    "iffco": {"name": "IFFCO Chowk", "lat": 28.4726, "lon": 77.0726},
    "mgroad": {"name": "MG Road", "lat": 28.4795, "lon": 77.0806},
    "cyberhub": {"name": "Cyber Hub", "lat": 28.4947, "lon": 77.0897},
    "golfcourse": {"name": "Golf Course Rd", "lat": 28.4503, "lon": 77.0972},
    "sohna": {"name": "Sohna Road", "lat": 28.4073, "lon": 77.0460},
    "nh48": {"name": "NH-48 (Ambience)", "lat": 28.5052, "lon": 77.0970},
    "rajiv": {"name": "Rajiv Chowk", "lat": 28.4691, "lon": 77.0366},
    "huda": {"name": "Huda City Centre", "lat": 28.4595, "lon": 77.0722},
    "sector56": {"name": "Sector 56", "lat": 28.4244, "lon": 77.1070},
    "manesar": {"name": "Manesar Rd", "lat": 28.3540, "lon": 76.9440},
}

# Default map center and zoom
DEFAULT_MAP_CENTER = [28.4595, 77.0266]
DEFAULT_MAP_ZOOM = 13

# ============================================================================
# PRINT CONFIGURATION SUMMARY
# ============================================================================
def print_config_summary():
    """Print configuration summary for debugging"""
    print("\n" + "=" * 70)
    print("[CONFIG] Configuration Summary")
    print("=" * 70)
    print(f"Project Root:        {PROJECT_ROOT}")
    print(f"Web Dir:             {WEB_DIR}")
    print(f"Collector Dir:       {COLLECTOR_DIR}")
    print(f"Collector Outputs:   {COLLECTOR_OUTPUTS}")
    print(f"Flask:               {FLASK_HOST}:{FLASK_PORT}")
    print(f"CORS Enabled:        {CORS_ENABLED}")
    print(f"CORS Origins:        {CORS_ORIGINS}")
    print(f"GeoPandas:           {GEOPANDAS_OK}")
    print(f"OSMnx:               {OSMNX_AVAILABLE}")
    print(f"Flood Geocoded Dir:  {FLOOD_GEOCODED_DIR.exists()}")
    print(f"Traffic Snapshots:   {TRAFFIC_SNAPSHOTS_DIR.exists()}")
    print(f"Graph Candidates:    {[p.exists() for p in GRAPH_CANDIDATES]}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    print_config_summary()
