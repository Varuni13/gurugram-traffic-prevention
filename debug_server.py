#!/usr/bin/env python3
"""
Debug script to compare local vs remote server environments.
Run this on BOTH your local machine and Linux server.
"""

import sys
import os
import platform
from pathlib import Path
from datetime import datetime, timezone, timedelta

print("=" * 70)
print("GURUGRAM TRAFFIC DASHBOARD - ENVIRONMENT DEBUG")
print("=" * 70)

# 1. SYSTEM INFO
print(f"\n[1] SYSTEM INFO")
print(f"    OS: {platform.system()} {platform.release()}")
print(f"    Python: {sys.version}")
print(f"    Platform: {platform.platform()}")
print(f"    Machine: {platform.machine()}")

# 2. PROJECT PATHS
print(f"\n[2] PROJECT STRUCTURE")
project_root = Path(__file__).resolve().parent
print(f"    Project Root: {project_root}")
print(f"    Exists: {project_root.exists()}")

critical_paths = {
    "config.py": project_root / "config.py",
    ".env": project_root / ".env",
    "web/": project_root / "web",
    "web/data/": project_root / "web" / "data",
    "web/data/GEOCODED/": project_root / "web" / "data" / "GEOCODED",
    "web/data/ggn_extent.graphml": project_root / "web" / "data" / "ggn_extent.graphml",
    "web/data/clean_roads.geojson": project_root / "web" / "data" / "clean_roads.geojson",
    "collector/outputs/": project_root / "collector" / "outputs",
    "web/data/cache/": project_root / "web" / "data" / "cache",
}

for name, path in critical_paths.items():
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"    {status} {name}: {path}")
    
    if exists and path.is_dir():
        try:
            # Check permissions
            test_file = path / ".test_write"
            test_file.touch()
            test_file.unlink()
            print(f"       → Writable: ✅")
        except Exception as e:
            print(f"       → Writable: ❌ ({e})")

# 3. ENVIRONMENT VARIABLES
print(f"\n[3] ENVIRONMENT VARIABLES")
env_vars = ["TOMTOM_API_KEY", "FLASK_HOST", "FLASK_PORT", "FLASK_DEBUG"]
for var in env_vars:
    value = os.getenv(var, "NOT SET")
    if var == "TOMTOM_API_KEY" and value != "NOT SET":
        # Mask API key
        value = f"{'*' * 20}{value[-4:]}" if len(value) > 4 else "SET (short)"
    print(f"    {var}: {value}")

# 4. PYTHON PACKAGES
print(f"\n[4] REQUIRED PACKAGES")
packages = {
    "flask": "Flask",
    "flask_cors": "Flask-CORS",
    "geopandas": "GeoPandas",
    "shapely": "Shapely",
    "networkx": "NetworkX",
    "osmnx": "OSMnx",
    "requests": "Requests",
}

for module, name in packages.items():
    try:
        __import__(module)
        print(f"    ✅ {name}")
    except ImportError:
        print(f"    ❌ {name} - NOT INSTALLED")

# 5. FILE COUNTS
print(f"\n[5] DATA FILE COUNTS")
geocoded_dir = project_root / "web" / "data" / "GEOCODED"
if geocoded_dir.exists():
    flood_files = list(geocoded_dir.glob("*.geojson"))
    d_files = [f for f in flood_files if f.stem.startswith('D')]
    print(f"    Total GeoJSON files: {len(flood_files)}")
    print(f"    Files starting with 'D': {len(d_files)}")
    if d_files:
        print(f"    First file: {d_files[0].name}")
        print(f"    Last file: {d_files[-1].name}")
else:
    print(f"    ❌ GEOCODED directory not found")

traffic_dir = project_root / "collector" / "outputs" / "traffic_snapshots"
if traffic_dir.exists():
    traffic_files = list(traffic_dir.glob("traffic_*.json"))
    print(f"    Traffic snapshots: {len(traffic_files)}")
    if traffic_files:
        print(f"    Latest: {traffic_files[-1].name}")
else:
    print(f"    ⚠️  Traffic snapshots directory not found")

# 6. TIMEZONE CHECK
print(f"\n[6] TIMEZONE INFO")
now_utc = datetime.now(timezone.utc)
now_local = datetime.now()
print(f"    UTC Time: {now_utc}")
print(f"    Local Time: {now_local}")
print(f"    Timezone offset: {now_local.utcoffset()}")

# Calculate IST manually
IST = timezone(timedelta(hours=5, minutes=30))
now_ist = datetime.now(IST)
print(f"    IST Time (manual): {now_ist}")

# 7. NETWORK CONNECTIVITY
print(f"\n[7] NETWORK CONNECTIVITY")
try:
    import requests
    
    # Test TomTom API endpoint
    test_url = "https://api.tomtom.com/search/2/geocode/gurugram.json"
    response = requests.get(test_url, params={"key": "test"}, timeout=5)
    print(f"    TomTom API reachable: ✅ (status: {response.status_code})")
except Exception as e:
    print(f"    TomTom API reachable: ❌ ({e})")

# 8. FILE SYSTEM CASE SENSITIVITY
print(f"\n[8] FILE SYSTEM CASE SENSITIVITY")
test_dir = project_root / "web" / "data"
if test_dir.exists():
    test_file = test_dir / "TEST_CASE.txt"
    try:
        test_file.write_text("test")
        
        # Try to access with different case
        test_file_lower = test_dir / "test_case.txt"
        if test_file_lower.exists():
            print(f"    Case-insensitive: ✅ (Windows-like)")
        else:
            print(f"    Case-sensitive: ✅ (Linux-like)")
        
        test_file.unlink()
    except Exception as e:
        print(f"    Could not test: {e}")

# 9. CACHE FILES
print(f"\n[9] CACHE STATUS")
cache_dir = project_root / "web" / "data" / "cache"
if cache_dir.exists():
    flood_cache = cache_dir / "flood_cache.json"
    route_cache = cache_dir / "route_cache.json"
    
    print(f"    Flood cache: {'✅' if flood_cache.exists() else '❌'}")
    if flood_cache.exists():
        print(f"       Size: {flood_cache.stat().st_size / 1024:.2f} KB")
    
    print(f"    Route cache: {'✅' if route_cache.exists() else '❌'}")
    if route_cache.exists():
        print(f"       Size: {route_cache.stat().st_size / 1024:.2f} KB")
else:
    print(f"    ❌ Cache directory not found")

print("\n" + "=" * 70)
print("DEBUG COMPLETE - Save this output for comparison")
print("=" * 70)