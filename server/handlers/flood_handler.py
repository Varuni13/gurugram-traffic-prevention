# server/handlers/flood_handler.py
"""
Flood data endpoint handlers.
Handles flood GeoJSON retrieval and flood-roads intersection.
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple, Any, List, Dict

from flask import jsonify

# Import global config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import config as global_config

# Optional geospatial libraries
if global_config.GEOPANDAS_OK:
    import geopandas as gpd

_FLOOD_ROADS_CACHE: Dict[str, Dict[str, Any]] = {}  # Cache for flood-roads data


def parse_ts_from_name(filename: str) -> Optional[datetime]:
    """
    Parse timestamp from flood filename format: DYYYYMMDDHHMM.geojson
    
    Args:
        filename: Flood file name
        
    Returns:
        Parsed datetime or None
    """
    try:
        stem = Path(filename).stem
        if not stem.startswith("D"):
            return None
        s = stem[1:13]  # YYYYMMDDHHMM
        return datetime.strptime(s, "%Y%m%d%H%M")
    except Exception:
        return None


def list_flood_files(
    start_dt: Optional[datetime] = None,
    end_dt: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Returns time-series flood files only.
    
    Args:
        start_dt: Optional start datetime filter
        end_dt: Optional end datetime filter
        
    Returns:
        List of flood file metadata dictionaries
    """
    out: List[Dict[str, Any]] = []
    flood_dir = global_config.FLOOD_GEOCODED_DIR

    if flood_dir.exists():
        files = sorted(flood_dir.glob("D*.geojson"))

        # Filter by time window if provided
        filtered = []
        for f in files:
            ts = parse_ts_from_name(f.name)
            if ts is None:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue
            filtered.append((ts, f))

        # Index continuously
        for i, (ts, f) in enumerate(filtered):
            out.append({
                "index": i,
                "filename": f.name,
                "label": ts.strftime("%Y-%m-%d %H:%M"),
                "timestamp": ts.isoformat()
            })

    return out


def resolve_flood_path_by_index(time_param: Optional[str]) -> Tuple[Path, Optional[str]]:
    """
    Resolve flood file path by index, filename, or use first available.
    
    Args:
        time_param: Can be index (int), filename, or None (first available)
        
    Returns:
        Tuple of (path, timestamp)
        
    Raises:
        FileNotFoundError: If file not found
    """
    flood_dir = global_config.FLOOD_GEOCODED_DIR
    files = list_flood_files()
    
    if not files:
        raise FileNotFoundError("No flood files found in FLOOD_GEOCODED_DIR")

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

    path = flood_dir / target["filename"]

    if not path.exists():
        raise FileNotFoundError(f"Flood file missing on disk: {path}")

    return path, target.get("timestamp")


def get_flood_data(time_param: Optional[str] = None) -> dict:
    """
    Get flood GeoJSON data.
    
    Args:
        time_param: Time index or filename
        
    Returns:
        GeoJSON dictionary
        
    Raises:
        FileNotFoundError: If flood file not found
    """
    try:
        path, _ = resolve_flood_path_by_index(time_param)
        with open(path, "r", encoding="utf-8") as f:
            return {"success": True, "data": f.read()}
    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))
    except Exception as e:
        raise Exception(f"Failed reading flood GeoJSON: {str(e)}")


def find_roads_file() -> Optional[Path]:
    """Find available roads GeoJSON file."""
    for p in global_config.ROADS_CANDIDATES:
        if p.exists():
            return p
    return None


def get_flooded_roads(time_param: Optional[str] = None) -> dict:
    """
    Get flooded road segments by intersecting roads with flood polygons.
    
    Args:
        time_param: Flood time index or filename
        
    Returns:
        GeoJSON FeatureCollection of flooded roads
        
    Raises:
        Exception: If geopandas not available or processing fails
    """
    if not global_config.GEOPANDAS_OK:
        raise Exception("geopandas/shapely not available")

    roads_path = find_roads_file()
    if not roads_path:
        raise FileNotFoundError("Road GeoJSON not found")

    try:
        flood_path, _ = resolve_flood_path_by_index(time_param)
        
        # Create cache key (unique identifier for this combination)
        cache_key = f"{roads_path.name}_{flood_path.name}"
        
        # Check if result is already cached
        if cache_key in _FLOOD_ROADS_CACHE:
            return _FLOOD_ROADS_CACHE[cache_key]

        roads = gpd.read_file(roads_path)
        flood = gpd.read_file(flood_path)

        if roads.empty:
            return {
                "type": "FeatureCollection",
                "features": [],
                "properties": {"note": "roads empty"}
            }

        if flood.empty:
            return {
                "type": "FeatureCollection",
                "features": [],
                "properties": {"note": "flood empty"}
            }

        # Ensure CRS compatibility
        if roads.crs is None:
            roads = roads.set_crs("EPSG:4326")
        if flood.crs is None:
            flood = flood.set_crs("EPSG:4326")
        if roads.crs != flood.crs:
            flood = flood.to_crs(roads.crs)

        # Keep only valid geometries
        flood = flood[flood.geometry.notnull()]
        roads = roads[roads.geometry.notnull()]

        # Spatial join for roads intersecting flood
        flood_poly = flood[~flood.geometry.is_empty].copy()
        roads_ln = roads[~roads.geometry.is_empty].copy()

        joined = gpd.sjoin(roads_ln, flood_poly[["geometry"]], how="inner", predicate="intersects")

        if joined.empty:
            return {
                "type": "FeatureCollection",
                "features": [],
                "properties": {
                    "roads_file": roads_path.name,
                    "flood_file": flood_path.name,
                    "count": 0
                }
            }

        # Deduplicate
        joined = joined.drop_duplicates(subset=[joined.index.name] if joined.index.name else None)
        joined["flooded"] = True

        import json
        out = json.loads(joined.to_json())
        out.setdefault("properties", {})
        out["properties"].update({
            "roads_file": roads_path.name,
            "flood_file": flood_path.name,
            "count": len(out.get("features", []))
        })
        
        # Save result to cache for future requests
        _FLOOD_ROADS_CACHE[cache_key] = out
        
        return out

    except FileNotFoundError as e:
        raise FileNotFoundError(str(e))
    except Exception as e:
        raise Exception(f"Failed flood->roads intersection: {str(e)}")
