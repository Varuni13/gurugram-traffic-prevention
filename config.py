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
FLASK_PORT = int(os.getenv("FLASK_PORT", "8000"))
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
# `MONITOR_POINTS` will be populated from `PRESET_LOCATIONS` defined
# later in this file so the web UI and collector stay in sync.
MONITOR_POINTS = []

COLLECTOR_INTERVAL_MIN = int(os.getenv("COLLECTOR_INTERVAL_MIN", "10"))

# ============================================================================
# ROUTING CONFIGURATION
# ============================================================================
# Flood depth threshold for obstacle detection
FLOOD_DEPTH_THRESHOLD_M = float(os.getenv("FLOOD_DEPTH_THRESHOLD_M", "0.3"))
FLOOD_PENALTY = float(os.getenv("FLOOD_PENALTY", "1000000.0"))

# Route cache settings
MAX_ROUTE_CACHE_SIZE = int(os.getenv("MAX_ROUTE_CACHE_SIZE", "500"))

# Persistent cache directory (survives server restarts)
CACHE_DIR = WEB_DIR / "data" / "cache"
FLOOD_CACHE_FILE = CACHE_DIR / "flood_cache.json"
ROUTE_CACHE_FILE = CACHE_DIR / "route_cache.json"

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

# Preset locations for web UI (expanded to match web/app.js 25 hotspots)
PRESET_LOCATIONS = {
    "iffco_chowk": {"name": "IFFCO Chowk", "lat": 28.477564199478913, "lon": 77.06859985177209},
    "rajiv_chowk": {"name": "Rajiv Chowk", "lat": 28.445292087715444, "lon": 77.03318302971367},
    "hero_honda": {"name": "Hero Honda Chowk", "lat": 28.429572485292674, "lon": 77.02009547931516},
    "kherki_daula": {"name": "Kherki Daula Toll Plaza", "lat": 28.395715221700556, "lon": 76.98214491369943},
    "signature_tower": {"name": "Signature Tower", "lat": 28.462211223747214, "lon": 77.0489446912307},
    "shankar_chowk": {"name": "Shankar Chowk / Cyber City", "lat": 28.508064947117724, "lon": 77.08211742534732},
    "sikanderpur": {"name": "Sikanderpur Metro", "lat": 28.481187691171193, "lon": 77.09425732449982},
    "huda_city": {"name": "HUDA City Centre Metro", "lat": 28.459382783815194, "lon": 77.07285799465937},
    "subhash_chowk": {"name": "Subhash Chowk", "lat": 28.428861106525773, "lon": 77.03711785417951},
    "jharsa_chowk": {"name": "Jharsa Chowk", "lat": 28.454834178543077, "lon": 77.04244784380403},
    "atul_kataria": {"name": "Atul Kataria Chowk", "lat": 28.481183722468575, "lon": 77.04867463883903},
    "mahavir_chowk": {"name": "Mahavir Chowk", "lat": 28.463656522868447, "lon": 77.03413268301684},
    "ghata_chowk": {"name": "Ghata Chowk", "lat": 28.421982117566415, "lon": 77.10973463698622},
    "vatika_chowk": {"name": "Vatika Chowk (SPR-Sohna Rd)", "lat": 28.404865793781532, "lon": 77.04204962349263},
    "badshahpur": {"name": "Badshahpur / Sohna Rd junction", "lat": 28.35048237859808, "lon": 77.0655043369831},
    "ambedkar_chowk": {"name": "Ambedkar Chowk", "lat": 28.437148333410683, "lon": 77.0674060560299},
    "dundahera": {"name": "Dundahera Hanuman Mandir (Old Delhi Rd)", "lat": 28.511407097088824, "lon": 77.07777883884035},
    "dwarka_nh48": {"name": "Dwarka Expwy-NH48 Cloverleaf", "lat": 28.40601139485718, "lon": 76.9902767658213},
    "sector31": {"name": "Sector 31 Signal / Market", "lat": 28.456542851852696, "lon": 77.04977988988432},
    "old_bus_stand": {"name": "Old Gurgaon Bus Stand", "lat": 28.466952871185878, "lon": 77.03269036613194},
    "imt_manesar": {"name": "IMT Manesar Junction", "lat": 28.360673595292468, "lon": 76.93919787004663},
    "golf_course": {"name": "Golf Course Rd - One Horizon", "lat": 28.4513013391806, "lon": 77.09741156582324},
    "sector56_57": {"name": "Sector 56/57 - Golf Course Extn", "lat": 28.448653219922612, "lon": 77.09931976915546},
    "sohna_entry": {"name": "Sohna Town Entry", "lat": 28.419803693042986, "lon": 77.04230448203113},
    "pataudi_rd": {"name": "Pataudi Rd - Sector 89/90", "lat": 28.427631686155653, "lon": 76.94592366161731}
}

# Derive collector monitor points from the web preset locations so both stay in sync
MONITOR_POINTS = list(PRESET_LOCATIONS.values())

# Traffic influence radius - edges within this distance of a traffic monitoring point
# will inherit that point's speed ratio (with distance-based decay)
# Larger radius = more edges affected, but slower computation on first run
TRAFFIC_INFLUENCE_RADIUS_M = float(os.getenv("TRAFFIC_INFLUENCE_RADIUS_M", "500"))

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
