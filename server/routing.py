# server/routing.py
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set
import math
import json
import time
import sys
from datetime import datetime, timedelta

import networkx as nx

# Import global configuration
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as global_config

# Use global config for libraries
GEOPANDAS_OK = global_config.GEOPANDAS_OK
OSMNX_AVAILABLE = global_config.OSMNX_AVAILABLE
gpd = global_config.gpd
ox = global_config.ox
LineString = global_config.LineString

PROJECT_ROOT = global_config.PROJECT_ROOT

DEFAULT_CANDIDATES = global_config.GRAPH_CANDIDATES
ROAD_GEOJSON_CANDIDATES = global_config.ROADS_CANDIDATES

_graph: Optional[nx.MultiDiGraph] = None
_gdf_edges = None
_graphml_path_used: Optional[Path] = None
_travel_time_initialized: bool = False  # Track if travel_time defaults are set

_roads_by_osmid: Optional[Dict[Any, List[Any]]] = None
_roads_geojson_path_used: Optional[Path] = None

# Flood cache: flood_index -> set of (u,v,k) edge keys that intersect flood
_flood_edge_cache: Dict[int, Set[Tuple[int, int, int]]] = {}
_flood_meta_cache: Dict[int, Dict[str, Any]] = {}  # logging/meta

# Traffic cache: (lat, lon) -> (u, v, k)
_traffic_cache: Dict[Tuple[float, float], Tuple[int, int, int]] = {}

_route_cache: Dict[Tuple[float, float, float, float, int, str], Dict[str, Any]] = {}
_route_cache_stats = {"hits": 0, "misses": 0}  # Track cache effectiveness

# Use global configuration constants
MAX_ROUTE_CACHE_SIZE = global_config.MAX_ROUTE_CACHE_SIZE
FLOOD_DEPTH_THRESHOLD_M = global_config.FLOOD_DEPTH_THRESHOLD_M
FLOOD_PENALTY = global_config.FLOOD_PENALTY

# Persistent cache paths
CACHE_DIR = global_config.CACHE_DIR
FLOOD_CACHE_FILE = global_config.FLOOD_CACHE_FILE
ROUTE_CACHE_FILE = global_config.ROUTE_CACHE_FILE


# ---------------------------
# Persistent Cache Functions
# ---------------------------
def _ensure_cache_dir():
    """Create cache directory if it doesn't exist."""
    if not CACHE_DIR.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"[Cache] Created cache directory: {CACHE_DIR}")


def save_flood_cache_to_disk() -> bool:
    """
    Save flood edge cache to disk for persistence across restarts.
    Returns True if successful.
    """
    global _flood_edge_cache
    if not _flood_edge_cache:
        print("[Cache] No flood cache to save")
        return False
    
    try:
        _ensure_cache_dir()
        
        # Convert sets to lists for JSON serialization
        export_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "entries_count": len(_flood_edge_cache),
            "entries": {
                str(k): [list(edge) for edge in v]
                for k, v in _flood_edge_cache.items()
            }
        }
        
        with open(FLOOD_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(export_data, f)
        
        print(f"[Cache] ✓ Saved flood cache ({len(_flood_edge_cache)} entries) to {FLOOD_CACHE_FILE.name}")
        return True
    except Exception as e:
        print(f"[Cache] ✗ Failed to save flood cache: {e}")
        return False


def load_flood_cache_from_disk() -> bool:
    """
    Load flood edge cache from disk.
    Returns True if cache was loaded successfully.
    """
    global _flood_edge_cache
    
    if not FLOOD_CACHE_FILE.exists():
        print(f"[Cache] No flood cache file found at {FLOOD_CACHE_FILE}")
        return False
    
    try:
        with open(FLOOD_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Convert lists back to sets of tuples
        for key, edges in data.get("entries", {}).items():
            _flood_edge_cache[int(key)] = set(tuple(e) for e in edges)
        
        created = data.get("created_at", "unknown")
        print(f"[Cache] ✓ Loaded flood cache ({len(_flood_edge_cache)} entries) from disk (created: {created})")
        return True
    except Exception as e:
        print(f"[Cache] ✗ Failed to load flood cache: {e}")
        return False


def save_route_cache_to_disk() -> bool:
    """
    Save route cache to disk for persistence across restarts.
    Returns True if successful.
    """
    global _route_cache
    if not _route_cache:
        print("[Cache] No route cache to save")
        return False
    
    try:
        _ensure_cache_dir()
        
        # Convert tuple keys to strings for JSON compatibility
        export_data = {
            "version": "1.0",
            "created_at": datetime.now().isoformat(),
            "stats": _route_cache_stats,
            "entries_count": len(_route_cache),
            "entries": {}
        }
        
        for key, val in _route_cache.items():
            # key is (origin_lat, origin_lon, dest_lat, dest_lon, flood_idx, route_type)
            key_str = f"{key[0]},{key[1]}_{key[2]},{key[3]}_{key[4]}_{key[5]}"
            export_data["entries"][key_str] = {
                "key_tuple": list(key),
                "route": val
            }
        
        with open(ROUTE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(export_data, f)
        
        print(f"[Cache] ✓ Saved route cache ({len(_route_cache)} routes) to {ROUTE_CACHE_FILE.name}")
        return True
    except Exception as e:
        print(f"[Cache] ✗ Failed to save route cache: {e}")
        return False


def load_route_cache_from_disk() -> bool:
    """
    Load route cache from disk.
    Returns True if cache was loaded successfully.
    """
    global _route_cache, _route_cache_stats
    
    if not ROUTE_CACHE_FILE.exists():
        print(f"[Cache] No route cache file found")
        return False
    
    try:
        with open(ROUTE_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Restore stats
        if "stats" in data:
            _route_cache_stats = data["stats"]
        
        # Convert string keys back to tuples
        for key_str, entry in data.get("entries", {}).items():
            key_tuple = tuple(entry["key_tuple"])
            _route_cache[key_tuple] = entry["route"]
        
        created = data.get("created_at", "unknown")
        print(f"[Cache] ✓ Loaded route cache ({len(_route_cache)} routes) from disk (created: {created})")
        return True
    except Exception as e:
        print(f"[Cache] ✗ Failed to load route cache: {e}")
        return False


def invalidate_caches():
    """
    Clear all caches (memory and disk). Call when flood data files change.
    """
    global _flood_edge_cache, _route_cache, _route_cache_stats
    
    _flood_edge_cache.clear()
    _route_cache.clear()
    _route_cache_stats = {"hits": 0, "misses": 0}
    
    # Delete disk cache files
    if FLOOD_CACHE_FILE.exists():
        FLOOD_CACHE_FILE.unlink()
    if ROUTE_CACHE_FILE.exists():
        ROUTE_CACHE_FILE.unlink()
    
    print("[Cache] ✓ All caches invalidated (memory and disk)")


# ---------------------------
# Graph load
# ---------------------------
def _pick_graphml_path() -> Path:
    for p in DEFAULT_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "GraphML file not found. Tried:\n" + "\n".join([f" - {str(p)}" for p in DEFAULT_CANDIDATES])
    )


def load_graph() -> nx.MultiDiGraph:
    global _graph, _graphml_path_used

    if _graph is not None:
        return _graph

    path = _pick_graphml_path()
    _graphml_path_used = path
    print(f"[Routing] Loading graph: {path}")

    if OSMNX_AVAILABLE:
        G = ox.load_graphml(str(path))
        _graph = G
        print("[Routing] Loaded using osmnx.load_graphml")
    else:
        G = nx.read_graphml(str(path))
        # Convert node IDs to int where possible
        mapping = {}
        for n in G.nodes:
            try:
                mapping[n] = int(n)
            except Exception:
                pass
        if mapping:
            G = nx.relabel_nodes(G, mapping)

        numeric_attrs = ["length", "travel_time", "maxspeed"]
        for u, v, k, data in G.edges(keys=True, data=True):
            for attr in numeric_attrs:
                if attr in data and isinstance(data[attr], str):
                    try:
                        data[attr] = float(data[attr])
                    except Exception:
                        pass

        _graph = G
        print("[Routing] Loaded using networkx.read_graphml")

    print(f"[Routing] Graph ready: nodes={_graph.number_of_nodes()} edges={_graph.number_of_edges()}")
    return _graph


def _ensure_gdf_edges():
    """
    Get edge GeoDataFrame (geometry) from OSMnx graph (fast spatial operations).
    This is CRITICAL for fast flood intersection via sjoin.
    """
    global _gdf_edges
    if _gdf_edges is not None:
        return _gdf_edges
    if not OSMNX_AVAILABLE:
        return None
    G = load_graph()
    _gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)
    return _gdf_edges


# ---------------------------
# Road GeoJSON fallback for curved drawing
# ---------------------------
def _pick_roads_geojson_path() -> Path:
    for p in ROAD_GEOJSON_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(
        "Road GeoJSON not found. Tried:\n" + "\n".join([f" - {str(p)}" for p in ROAD_GEOJSON_CANDIDATES])
    )


def _normalize_osmid(val: Any) -> List[Any]:
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        out: List[Any] = []
        for x in val:
            out.extend(_normalize_osmid(x))
        return out
    if isinstance(val, (int, float)):
        try:
            return [int(val)]
        except Exception:
            return [val]
    if isinstance(val, str):
        s = val.strip()
        if ";" in s or "," in s:
            parts = [p.strip() for p in s.replace(",", ";").split(";") if p.strip()]
            out: List[Any] = []
            for p in parts:
                out.extend(_normalize_osmid(p))
            return out
        try:
            return [int(s), s]
        except Exception:
            return [s]
    return [val]


def _ensure_roads_by_osmid() -> Dict[Any, List[Any]]:
    global _roads_by_osmid, _roads_geojson_path_used
    if _roads_by_osmid is not None:
        return _roads_by_osmid

    try:
        import geopandas as gpd_local
    except Exception:
        print("[Routing] geopandas not available; curved drawing disabled.")
        _roads_by_osmid = {}
        return _roads_by_osmid

    path = _pick_roads_geojson_path()
    _roads_geojson_path_used = path
    print(f"[Routing] Loading roads geojson: {path}")

    gdf = gpd_local.read_file(path)
    gdf = gdf[gdf.geometry.type == "LineString"].copy()

    id_col = None
    for c in ["osmid", "osm_id", "osmId", "OSM_ID"]:
        if c in gdf.columns:
            id_col = c
            break
    if id_col is None:
        print("[Routing] No osmid/osm_id in road geojson; curved drawing disabled.")
        _roads_by_osmid = {}
        return _roads_by_osmid

    roads_by: Dict[Any, List[Any]] = {}
    for _, row in gdf.iterrows():
        oid = row.get(id_col)
        if oid is None:
            continue
        keys = _normalize_osmid(oid)
        geom = row.geometry
        for k in keys:
            roads_by.setdefault(k, []).append(geom)

    print(f"[Routing] Roads loaded: {len(gdf)} LineStrings, {len(roads_by)} unique keys")
    _roads_by_osmid = roads_by
    return _roads_by_osmid


def _edge_geometry_points_from_geojson(u: int, v: int, k: int, G: nx.MultiDiGraph) -> List[Tuple[float, float]]:
    roads_by = _ensure_roads_by_osmid()
    if not roads_by:
        return []
    data = G.get_edge_data(u, v, k) or {}
    osmids = _normalize_osmid(data.get("osmid"))
    if not osmids:
        return []
    for oid in osmids:
        geoms = roads_by.get(oid)
        if geoms:
            geom = geoms[0]
            try:
                return list(geom.coords)
            except Exception:
                return []
    return []


# ---------------------------
# Helpers
# ---------------------------
def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


# ---------------------------
# Traffic snapshot + apply
# ---------------------------
def load_traffic_snapshot() -> List[Dict]:
    traffic_file = PROJECT_ROOT / "web" / "data" / "latest_traffic.json"
    if not traffic_file.exists():
        return []
    try:
        with open(traffic_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("points", [])
    except Exception:
        return []


def _parse_maxspeed_kph(val, default_kph: float) -> float:
    if val is None:
        return default_kph
    try:
        if isinstance(val, (list, tuple)) and val:
            val = val[0]
        if isinstance(val, (int, float)):
            return float(val)
        if isinstance(val, str):
            digits = "".join(ch for ch in val if (ch.isdigit() or ch == "."))
            return float(digits) if digits else default_kph
    except Exception:
        return default_kph
    return default_kph


def _initialize_travel_time_defaults(G: nx.MultiDiGraph) -> None:
    """
    ONE-TIME initialization: Calculate default travel_time for ALL edges.
    Called once when graph loads, not on every request.
    """
    global _travel_time_initialized
    if _travel_time_initialized:
        return  # Already initialized
    
    DEFAULT_SPEED_KPH = 30.0
    print("[Routing] Initializing travel_time for all edges (one-time)...")
    
    for u, v, k, data in G.edges(keys=True, data=True):
        length = float(data.get("length", 100.0))
        ff_kph = float(data.get("free_flow_kph", _parse_maxspeed_kph(data.get("maxspeed"), DEFAULT_SPEED_KPH)))
        data["free_flow_kph"] = ff_kph
        data["speed_ratio"] = 1.0
        data["has_traffic"] = False
        data["current_speed_kph"] = ff_kph
        speed_mps = ff_kph * 1000.0 / 3600.0
        data["travel_time"] = length / speed_mps if speed_mps > 0 else length / 8.33
    
    _travel_time_initialized = True
    print(f"[Routing] travel_time initialized for {G.number_of_edges()} edges")


# Traffic influence radius in meters - edges within this distance of a traffic point
# will inherit that point's speed ratio (with distance-based decay)
TRAFFIC_INFLUENCE_RADIUS_M = getattr(global_config, 'TRAFFIC_INFLUENCE_RADIUS_M', 500)  # default 500m

# Cache for edges within radius of each traffic point
_traffic_radius_cache: Dict[Tuple[float, float], List[Tuple[int, int, int, float]]] = {}


def _find_edges_within_radius(G: nx.MultiDiGraph, lat: float, lon: float, radius_m: float) -> List[Tuple[int, int, int, float]]:
    """
    Find all edges within radius_m of a point.
    Returns list of (u, v, k, distance_m) tuples.
    """
    edges_in_radius = []
    
    for u, v, k, data in G.edges(keys=True, data=True):
        # Get edge midpoint (approximate)
        u_data = G.nodes[u]
        v_data = G.nodes[v]
        
        u_lat = float(u_data.get("y", 0))
        u_lon = float(u_data.get("x", 0))
        v_lat = float(v_data.get("y", 0))
        v_lon = float(v_data.get("x", 0))
        
        # Use midpoint of edge
        mid_lat = (u_lat + v_lat) / 2
        mid_lon = (u_lon + v_lon) / 2
        
        # Calculate distance from traffic point to edge midpoint
        dist = _haversine_m(lat, lon, mid_lat, mid_lon)
        
        if dist <= radius_m:
            edges_in_radius.append((u, v, k, dist))
    
    return edges_in_radius


# Traffic assignment strategy options
TRAFFIC_STRATEGY = "nearest"  # Options: "nearest", "worst", "weighted_average"


def apply_traffic_data(G: nx.MultiDiGraph, traffic_points: List[Dict]) -> None:
    """
    Apply traffic data from monitoring points to ALL nearby edges within radius.
    
    Strategy options (set TRAFFIC_STRATEGY above):
    - "nearest": Use the closest traffic point's data (most accurate)
    - "worst": Use the slowest speed ratio (conservative, avoids congestion)
    - "weighted_average": Blend all nearby points by distance (smooth but less accurate)
    
    This ensures custom routes passing near traffic points use real speeds
    instead of default free-flow speeds.
    """
    global _traffic_radius_cache
    DEFAULT_SPEED_KPH = 30.0
    
    # Ensure defaults are initialized (one-time)
    _initialize_travel_time_defaults(G)
    
    if not traffic_points:
        return

    # Parse traffic points
    traffic_data = []
    for p in traffic_points:
        lat = float(p.get("lat") or p.get("query_lat") or 0)
        lon = float(p.get("lon") or p.get("query_lon") or 0)
        sr = float(p.get("speed_ratio", 1.0))
        if not lat or not lon:
            continue
        sr = max(0.1, min(sr, 1.0))
        traffic_data.append((lat, lon, sr))

    if not traffic_data:
        return

    # For each edge, track: {edge_key: [(distance, speed_ratio, decay_factor), ...]}
    edge_traffic_info: Dict[Tuple[int, int, int], List[Tuple[float, float, float]]] = {}
    count_updated = 0
    
    # Step 1: Collect all traffic points that affect each edge
    for lat, lon, sr in traffic_data:
        cache_key = (round(lat, 6), round(lon, 6))
        
        # Check cache for edges within radius
        if cache_key in _traffic_radius_cache:
            edges_nearby = _traffic_radius_cache[cache_key]
        else:
            # Find all edges within radius (slower, but cached)
            edges_nearby = _find_edges_within_radius(G, lat, lon, TRAFFIC_INFLUENCE_RADIUS_M)
            _traffic_radius_cache[cache_key] = edges_nearby
        
        # Record this traffic point's influence on each nearby edge
        for (u, v, k, dist) in edges_nearby:
            # Distance decay: closer = stronger influence
            # At 0m: factor = 1.0, at radius: factor = 0.3
            decay_factor = max(0.3, 1.0 - (dist / TRAFFIC_INFLUENCE_RADIUS_M) * 0.7)
            
            uvk = (u, v, k)
            if uvk not in edge_traffic_info:
                edge_traffic_info[uvk] = []
            edge_traffic_info[uvk].append((dist, sr, decay_factor))
    
    # Step 2: For each edge, choose the best traffic data based on strategy
    for uvk, traffic_list in edge_traffic_info.items():
        
        if TRAFFIC_STRATEGY == "nearest":
            # ═══════════════════════════════════════════════════════════════
            # NEAREST: Use the closest traffic point's speed ratio
            # Logic: The sensor closest to this road knows its condition best
            # ═══════════════════════════════════════════════════════════════
            nearest = min(traffic_list, key=lambda x: x[0])  # x[0] = distance
            dist, sr, decay = nearest
            effective_sr = sr * decay + 1.0 * (1 - decay)
            
        elif TRAFFIC_STRATEGY == "worst":
            # ═══════════════════════════════════════════════════════════════
            # WORST: Use the slowest (lowest) speed ratio
            # Logic: Conservative - assume worst case to avoid congestion
            # ═══════════════════════════════════════════════════════════════
            effective_sr = 1.0
            for dist, sr, decay in traffic_list:
                candidate_sr = sr * decay + 1.0 * (1 - decay)
                if candidate_sr < effective_sr:
                    effective_sr = candidate_sr
                    
        elif TRAFFIC_STRATEGY == "weighted_average":
            # ═══════════════════════════════════════════════════════════════
            # WEIGHTED AVERAGE: Blend all nearby points by inverse distance
            # Logic: Smooth result, but can dilute strong signals
            # ═══════════════════════════════════════════════════════════════
            total_weight = 0.0
            weighted_sum = 0.0
            for dist, sr, decay in traffic_list:
                # Weight = inverse distance (closer = higher weight)
                weight = 1.0 / max(dist, 1.0)  # Avoid division by zero
                candidate_sr = sr * decay + 1.0 * (1 - decay)
                weighted_sum += candidate_sr * weight
                total_weight += weight
            effective_sr = weighted_sum / total_weight if total_weight > 0 else 1.0
            
        else:
            # Default to nearest
            nearest = min(traffic_list, key=lambda x: x[0])
            dist, sr, decay = nearest
            effective_sr = sr * decay + 1.0 * (1 - decay)
        
        # Apply the chosen speed ratio to this edge
        u, v, k = uvk
        data = G.get_edge_data(u, v, k)
        if data:
            _update_edge_traffic(data, effective_sr)
            count_updated += 1

    print(f"[Routing] Updated {count_updated} edges with traffic data (strategy={TRAFFIC_STRATEGY}, radius={TRAFFIC_INFLUENCE_RADIUS_M}m, {len(traffic_data)} points)")


def _update_edge_traffic(data: Dict, sr: float):
    DEFAULT_SPEED_KPH = 30.0
    length = float(data.get("length", 100.0))
    ff_kph = float(data.get("free_flow_kph", DEFAULT_SPEED_KPH))

    data["speed_ratio"] = sr
    data["has_traffic"] = sr < 0.8
    data["current_speed_kph"] = ff_kph * sr

    speed_mps = data["current_speed_kph"] * 1000.0 / 3600.0
    data["travel_time"] = length / speed_mps if speed_mps > 0 else length / 8.33


# ---------------------------
# Nearest nodes
# ---------------------------
def find_nearest_node(lat: float, lon: float) -> int:
    G = load_graph()
    if OSMNX_AVAILABLE:
        return int(ox.distance.nearest_nodes(G, X=lon, Y=lat))

    best = None
    best_d = float("inf")
    for n, data in G.nodes(data=True):
        y = float(data.get("y", data.get("lat", 0.0)))
        x = float(data.get("x", data.get("lon", 0.0)))
        d = (lat - y) ** 2 + (lon - x) ** 2
        if d < best_d:
            best_d = d
            best = n
    if best is None:
        raise RuntimeError("Could not find nearest node")
    return int(best)


def find_routable_node(lat: float, lon: float, dest_node: Optional[int] = None, k: int = 30) -> int:
    G = load_graph()
    if not OSMNX_AVAILABLE:
        return find_nearest_node(lat, lon)

    n0 = int(ox.distance.nearest_nodes(G, X=lon, Y=lat))
    if G.out_degree(n0) > 0 and (dest_node is None or nx.has_path(G, n0, dest_node)):
        return n0

    gdf_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)
    ys = gdf_nodes["y"].to_numpy()
    xs = gdf_nodes["x"].to_numpy()
    dists = [_haversine_m(lat, lon, float(y), float(x)) for y, x in zip(ys, xs)]
    gdf_nodes = gdf_nodes.copy()
    gdf_nodes["dist_m"] = dists
    candidates = gdf_nodes.nsmallest(k, "dist_m")

    for node_id in candidates.index.tolist():
        nid = int(node_id)
        if G.out_degree(nid) <= 0:
            continue
        if dest_node is not None and not nx.has_path(G, nid, dest_node):
            continue
        return nid

    return n0


# ---------------------------
# Geometry for rendering
# ---------------------------
def _best_edge_key(G: nx.MultiDiGraph, u: int, v: int) -> int:
    edict = G.get_edge_data(u, v)
    if edict is None:
        return 0
    return int(min(edict.keys(), key=lambda kk: float(edict[kk].get("length", 1e18))))


def _route_nodes_to_edges(route_nodes: List[int], G: nx.MultiDiGraph) -> List[Tuple[int, int, int]]:
    edges = []
    for a, b in zip(route_nodes[:-1], route_nodes[1:]):
        k = _best_edge_key(G, int(a), int(b))
        edges.append((int(a), int(b), int(k)))
    return edges


def _edges_to_linestring_coords_lonlat(edges: List[Tuple[int, int, int]], G: nx.MultiDiGraph) -> List[List[float]]:
    coords: List[Tuple[float, float]] = []
    gdf_edges = _ensure_gdf_edges()

    for i, (u, v, k) in enumerate(edges):
        pts: List[Tuple[float, float]] = []

        if gdf_edges is not None:
            try:
                geom = gdf_edges.loc[(u, v, k)].geometry
                if geom is not None:
                    pts = list(geom.coords)
            except Exception:
                pts = []

        if not pts:
            pts = _edge_geometry_points_from_geojson(u, v, k, G)

        if not pts:
            udata = G.nodes[u]
            vdata = G.nodes[v]
            pts = [
                (float(udata.get("x")), float(udata.get("y"))),
                (float(vdata.get("x")), float(vdata.get("y"))),
            ]

        if i == 0:
            coords.extend(pts)
        else:
            if coords and pts and coords[-1] == pts[0]:
                coords.extend(pts[1:])
            else:
                coords.extend(pts)

    return [[float(lon), float(lat)] for lon, lat in coords]


# ---------------------------
# FLOOD: fast intersection + caching
# ---------------------------
def _flood_file_for_index(flood_idx: int) -> Optional[Path]:
    flood_dir = PROJECT_ROOT / "web" / "data" / "GEOCODED"
    files = sorted(flood_dir.glob("D*.geojson"))
    if not files:
        return None
    if 0 <= flood_idx < len(files):
        return files[flood_idx]
    # fallback
    return files[0]


def _detect_depth_column(gdf: "gpd.GeoDataFrame") -> Optional[str]:
    for col in ["depth", "flood_depth", "water_depth", "wd"]:
        if col in gdf.columns:
            return col
    return None


def _compute_flooded_edges_set(flood_idx: int) -> Set[Tuple[int, int, int]]:
    """
    Compute once using GeoPandas sjoin (spatial index).
    Returns set of edge keys (u,v,k) that intersect flooded polygons.
    """
    if not GEOPANDAS_OK or not OSMNX_AVAILABLE:
        return set()

    gdf_edges = _ensure_gdf_edges()
    if gdf_edges is None or gdf_edges.empty:
        return set()

    flood_path = _flood_file_for_index(flood_idx)
    if not flood_path or not flood_path.exists():
        return set()

    t0 = time.perf_counter()
    flood_gdf = gpd.read_file(flood_path)
    if flood_gdf.empty:
        return set()

    # keep only polygons (your files are polygons)
    flood_gdf = flood_gdf[flood_gdf.geometry.notnull() & ~flood_gdf.geometry.is_empty].copy()
    if flood_gdf.empty:
        return set()

    depth_col = _detect_depth_column(flood_gdf)
    if depth_col:
        try:
            flood_gdf = flood_gdf[flood_gdf[depth_col] > FLOOD_DEPTH_THRESHOLD_M].copy()
        except Exception:
            pass
    if flood_gdf.empty:
        return set()

    # CRS normalize
    if gdf_edges.crs is None:
        gdf_edges = gdf_edges.set_crs("EPSG:4326")
    if flood_gdf.crs is None:
        flood_gdf = flood_gdf.set_crs("EPSG:4326")
    if flood_gdf.crs != gdf_edges.crs:
        flood_gdf = flood_gdf.to_crs(gdf_edges.crs)

    # OPTIMIZATION: Filter edges by total flood bounds first
    # This prevents checking 100k edges against polygons if they are far away
    try:
        bounds = flood_gdf.total_bounds # [minx, miny, maxx, maxy]
        minx, miny, maxx, maxy = bounds
        # Use cx indexer for fast bbox filtering
        candidates = gdf_edges.cx[minx:maxx, miny:maxy]
    except Exception as e:
        print(f"[Routing] BBox filter failed ({e}), using all edges")
        candidates = gdf_edges

    if candidates.empty:
         return set()

    # Keep only needed columns
    edges_geom = candidates[["geometry"]].copy()

    # Spatial join: edges that intersect flood polygons
    joined = gpd.GeoDataFrame()
    try:
        joined = gpd.sjoin(edges_geom, flood_gdf[["geometry"]], how="inner", predicate="intersects")
    except Exception as e:
        print(f"[Routing] ERROR in sjoin: {e}")
        return set()

    flooded: Set[Tuple[int, int, int]] = set()
    if not joined.empty:
        # joined index is MultiIndex (u,v,k)
        for idx in joined.index:
            try:
                # Handle cases where index might be simple or multi
                if isinstance(idx, tuple) and len(idx) >= 3:
                    u, v, k = idx[:3]
                else:
                    # sometimes reset_index might be needed if sjoin behaves differently
                    continue
                flooded.add((int(u), int(v), int(k)))
            except Exception:
                continue

    dt = time.perf_counter() - t0
    _flood_meta_cache[flood_idx] = {
        "flood_file": flood_path.name,
        "polygons_used": int(len(flood_gdf)),
        "edges_flooded": int(len(flooded)),
        "seconds": round(dt, 3),
    }
    print(f"[Routing] Flood cache build idx={flood_idx} flooded_edges={len(flooded)} in {dt:.2f}s ({flood_path.name})")
    return flooded


def _get_flooded_edges_set(flood_idx: int) -> Set[Tuple[int, int, int]]:
    if flood_idx in _flood_edge_cache:
        return _flood_edge_cache[flood_idx]
    flooded = _compute_flooded_edges_set(flood_idx)
    _flood_edge_cache[flood_idx] = flooded
    return flooded


def precompute_all_flood_data():
    """
    Called at startup to load all flood data into memory.
    OPTIMIZED: First tries to load from disk cache, skipping expensive computation.
    """
    # TRY TO LOAD FROM DISK FIRST (instant startup!)
    if load_flood_cache_from_disk():
        print("[Cache] ✓ Using cached flood data - skipping computation!")
        # Also try to load route cache
        load_route_cache_from_disk()
        return  # Done! No need to compute
    
    print("[Routing] Computing flood intersections (this will be saved to disk)...")
    flood_dir = PROJECT_ROOT / "web" / "data" / "GEOCODED"
    traffic_dir = PROJECT_ROOT / "collector" / "outputs" / "traffic_snapshots"
    
    if not flood_dir.exists():
        print("[Routing] No flood dir found, skipping pre-compute.")
        return

    # 1. Identify all available traffic timestamps
    traffic_timestamps = []
    if traffic_dir.exists():
        for t_file in traffic_dir.glob("traffic_*.json"):
            try:
                # filename: traffic_2026-01-08T12-47-09.828164+00-00.json
                # parse: 2026-01-08T12-47-09
                ts_str = t_file.stem.replace("traffic_", "").replace("-", ":", 2).replace("-", ":")
                ts_str = ts_str[:19].replace(":", "-", 2)
                dt = datetime.fromisoformat(ts_str)
                traffic_timestamps.append(dt)
            except Exception:
                continue
    
    print(f"[Routing] Found {len(traffic_timestamps)} traffic snapshots.")
    
    flood_files = sorted(flood_dir.glob("D*.geojson"))
    print(f"[Routing] Found {len(flood_files)} potential flood files.")
    
    # Ensure graph & gdf_edges loaded
    load_graph()
    if OSMNX_AVAILABLE:
        _ensure_gdf_edges()

    cached_count = 0
    skipped_count = 0

    for i, f_file in enumerate(flood_files):
        # 2. Find the NEAREST PREVIOUS traffic snapshot BY TIME OF DAY (ignoring date)
        should_cache = False
        matched_traffic = None
        
        try:
            # filename: D202601081230.geojson
            stem = f_file.stem
            if stem.startswith("D"):
                s = stem[1:13] # YYYYMMDDHHMM
                flood_dt = datetime.strptime(s, "%Y%m%d%H%M")
                
                # Extract TIME only (hour, minute) for matching
                flood_time = flood_dt.time()  # Just HH:MM:SS
                
                if traffic_timestamps:
                    # CRITICAL: Traffic timestamps are in UTC, flood filenames are in IST
                    # Convert traffic to IST (+5:30) before comparing
                    ist_offset = timedelta(hours=5, minutes=30)
                    traffic_times_ist = [(t, (t + ist_offset).time()) for t in traffic_timestamps]
                    
                    # Get the min and max traffic times (in IST) for range checking
                    min_traffic_time = min(tm for (dt, tm) in traffic_times_ist)
                    max_traffic_time = max(tm for (dt, tm) in traffic_times_ist)
                    
                    # Skip flood data that's outside the traffic time range
                    # Allow 30 minutes before/after for matching flexibility
                    flood_seconds = flood_time.hour * 3600 + flood_time.minute * 60
                    min_traffic_seconds = min_traffic_time.hour * 3600 + min_traffic_time.minute * 60 - 1800  # -30 min
                    max_traffic_seconds = max_traffic_time.hour * 3600 + max_traffic_time.minute * 60 + 1800  # +30 min
                    
                    if flood_seconds < min_traffic_seconds or flood_seconds > max_traffic_seconds:
                        print(f"[Routing] ✗ Skipping Flood {flood_time.strftime('%H:%M')} (outside traffic window {min_traffic_time.strftime('%H:%M')} IST - {max_traffic_time.strftime('%H:%M')} IST)")
                        # Don't cache - outside traffic range
                        continue
                    
                    # Find nearest PREVIOUS traffic by time of day (both in IST now)
                    previous_snapshots = [(dt, tm) for (dt, tm) in traffic_times_ist if tm <= flood_time]
                    
                    if previous_snapshots:
                        # Pick the CLOSEST previous one by time
                        matched_traffic_tuple = max(previous_snapshots, key=lambda x: x[1])
                        matched_traffic = matched_traffic_tuple[0]
                        matched_time = matched_traffic_tuple[1]
                        
                        # Calculate time difference (in seconds, ignoring date)
                        flood_seconds = flood_time.hour * 3600 + flood_time.minute * 60 + flood_time.second
                        traffic_seconds = matched_time.hour * 3600 + matched_time.minute * 60 + matched_time.second
                        diff_seconds = abs(flood_seconds - traffic_seconds)
                        
                        # Only match if within reasonable window (e.g., 2 hours)
                        if diff_seconds <= 7200:  # 2 hours = 7200 seconds
                            should_cache = True
                            # Show TIMES ONLY in IST for clarity
                            print(f"[Routing] ✓ Flood {flood_time.strftime('%H:%M')} IST → Traffic {matched_time.strftime('%H:%M')} IST (diff: {int(diff_seconds/60)}min)")
                        else:
                            print(f"[Routing] ✗ Flood {flood_time.strftime('%H:%M')} IST too far from nearest traffic (>{int(diff_seconds/60)}min)")
                    else:
                        # No previous traffic by time, try next one as fallback
                        future_snapshots = [(dt, tm) for (dt, tm) in traffic_times_ist if tm > flood_time]
                        if future_snapshots:
                            matched_traffic_tuple = min(future_snapshots, key=lambda x: x[1])
                            matched_traffic = matched_traffic_tuple[0]
                            matched_time = matched_traffic_tuple[1]
                            
                            flood_seconds = flood_time.hour * 3600 + flood_time.minute * 60 + flood_time.second
                            traffic_seconds = matched_time.hour * 3600 + matched_time.minute * 60 + matched_time.second
                            diff_seconds = abs(flood_seconds - traffic_seconds)
                            
                            if diff_seconds <= 7200:
                                should_cache = True
                                print(f"[Routing] ⚠️ Flood {flood_time.strftime('%H:%M')} IST → Traffic {matched_time.strftime('%H:%M')} IST (next: {int(diff_seconds/60)}min, no prev available)")
                        else:
                            print(f"[Routing] ✗ Flood {flood_time.strftime('%H:%M')} IST has no nearby traffic data")
                else:
                    print(f"[Routing] ✗ No traffic snapshots available")
                    
        except Exception as e:
            print(f"[Routing] Failed to parse flood timestamp from {f_file.name}: {e}")
            
        # FALLBACK: Cache index 0 only if NO other files were cached yet
        if i == 0 and not should_cache and cached_count == 0:
            print(f"[Routing] ⚠️ WARNING: Caching index 0 as fallback (NO traffic match!)")
            should_cache = True

        if should_cache:
            _get_flooded_edges_set(i)
            cached_count += 1
        else:
            skipped_count += 1
        
    print(f"[Routing] Pre-computation complete. Cached {cached_count} timestamps (Skipped {skipped_count} unmatched).")
    
    # SAVE TO DISK for next startup (instant load!)
    save_flood_cache_to_disk()


def _apply_flood_costs(G: nx.MultiDiGraph, flooded_edges: Set[Tuple[int, int, int]]) -> None:
    """
    IMPORTANT: do not scan all edges with geometry checks.
    Just set cost fields and then add penalty only for flooded edges.
    """
    # Base costs for all edges (cheap attributes only)
    for u, v, k, data in G.edges(keys=True, data=True):
        length = float(data.get("length", 100.0))
        tt = float(data.get("travel_time", length / 8.33))
        data["is_flooded"] = False
        data["flood_cost"] = length
        data["smart_cost"] = tt

    # Apply penalty only to flooded edges
    for (u, v, k) in flooded_edges:
        data = G.get_edge_data(u, v, k)
        if not data:
            continue
        # networkx returns dict for multi-edge
        if isinstance(data, dict) and "length" not in data:
            # data is keyed by k
            data = data.get(k, {})
        length = float(data.get("length", 100.0))
        tt = float(data.get("travel_time", length / 8.33))
        data["is_flooded"] = True
        data["flood_cost"] = length + FLOOD_PENALTY
        data["smart_cost"] = tt + FLOOD_PENALTY


# ---------------------------
# Main route API
# ---------------------------
def find_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    route_type: str = "shortest",
    flood_time: Optional[str] = None,
) -> Dict[str, Any]:
    """
    route_type:
      - shortest:     minimize length
      - fastest:      minimize travel_time (traffic)
      - flood_avoid:  minimize flood_cost (length + penalty on flooded)
      - smart:        minimize smart_cost (travel_time + penalty on flooded)
    """
    # PROGRESSIVE CACHE: Check if we've calculated this exact route before
    try:
        flood_idx = int(flood_time) if flood_time is not None else 0
    except Exception:
        flood_idx = 0
    
    # Create cache key (round coords to avoid float precision issues)
    cache_key = (
        round(origin_lat, 5),
        round(origin_lon, 5),
        round(dest_lat, 5),
        round(dest_lon, 5),
        flood_idx,
        route_type
    )
    
    # Check cache first
    if cache_key in _route_cache:
        _route_cache_stats["hits"] += 1
        hit_rate = (_route_cache_stats["hits"] / (_route_cache_stats["hits"] + _route_cache_stats["misses"])) * 100
        print(f"[Cache HIT] Returning cached route (hit rate: {hit_rate:.1f}%, cache size: {len(_route_cache)})")
        return _route_cache[cache_key]
    
    # Cache MISS - calculate the route
    _route_cache_stats["misses"] += 1
    print(f"[Cache MISS] Calculating new route (cache size: {len(_route_cache)})")
    
    t_start = time.perf_counter()
    G = load_graph()

    # 1) Traffic - SKIP for "shortest" route (only needs length attribute)
    t0 = time.perf_counter()
    t_traffic = 0.0
    if route_type in ("fastest", "smart"):
        traffic_points = load_traffic_snapshot()
        apply_traffic_data(G, traffic_points)
        t_traffic = time.perf_counter() - t0

    flooded_edges: Set[Tuple[int, int, int]] = set()
    t_flood = 0.0

    # 2) Flood costs only if needed
    if route_type in ("flood_avoid", "smart"):
        t1 = time.perf_counter()
        try:
            flood_idx = int(flood_time) if flood_time is not None else 0
        except Exception:
            flood_idx = 0

        flooded_edges = _get_flooded_edges_set(flood_idx)
        _apply_flood_costs(G, flooded_edges)
        t_flood = time.perf_counter() - t1
        
        # DEBUG: Log flood info
        print(f"[Flood Debug] route_type={route_type}, flood_idx={flood_idx}")
        print(f"[Flood Debug] Total flooded edges: {len(flooded_edges)}")
        if flooded_edges:
            sample = list(flooded_edges)[:5]
            print(f"[Flood Debug] Sample flooded edges: {sample}")

    # 3) Nodes
    dest_node = find_routable_node(dest_lat, dest_lon, dest_node=None, k=30)
    origin_node = find_routable_node(origin_lat, origin_lon, dest_node=dest_node, k=40)

    if origin_node == dest_node:
        return {"type": "FeatureCollection", "features": [], "error": "Origin and destination are the same"}

    # 4) Weight
    if route_type == "fastest":
        weight = "travel_time"
    elif route_type == "flood_avoid":
        weight = "flood_cost"
    elif route_type == "smart":
        weight = "smart_cost"
    else:
        weight = "length"

    # 5) Solve shortest path
    t2 = time.perf_counter()
    try:
        route_nodes = nx.shortest_path(G, origin_node, dest_node, weight=weight)
    except nx.NetworkXNoPath:
        return {"type": "FeatureCollection", "features": [], "error": "No path found"}
    except Exception as e:
        return {"type": "FeatureCollection", "features": [], "error": str(e)}
    t_path = time.perf_counter() - t2

    route_edges = _route_nodes_to_edges(route_nodes, G)

    distance_m = 0.0
    travel_time_s = 0.0
    flooded_distance_m = 0.0
    has_any_flood = False
    flooded_edge_list = []  # Track flooded edges for separate rendering

    for (u, v, k) in route_edges:
        data = G.get_edge_data(u, v, k) or {}
        length = float(data.get("length", 0.0))
        tt = float(data.get("travel_time", length / 8.33))
        distance_m += length
        travel_time_s += tt
        if data.get("is_flooded", False):
            flooded_distance_m += length
            has_any_flood = True
            flooded_edge_list.append((u, v, k))

    # DEBUG: Log route flood analysis
    if route_type in ("flood_avoid", "smart"):
        flooded_count = sum(1 for (u,v,k) in route_edges if G.get_edge_data(u,v,k) and G.get_edge_data(u,v,k).get("is_flooded"))
        print(f"[Flood Debug] Route has {len(route_edges)} edges, {flooded_count} are FLOODED")
        print(f"[Flood Debug] has_any_flood={has_any_flood}, flooded_distance={flooded_distance_m:.1f}m")

    coords = _edges_to_linestring_coords_lonlat(route_edges, G)
    
    # Get coordinates for each flooded segment SEPARATELY (for overlay rendering)
    # Use MultiLineString since flooded edges may not be contiguous
    flooded_multi_coords = []
    if flooded_edge_list:
        for (u, v, k) in flooded_edge_list:
            # Get coords for this single edge
            edge_coords = _edges_to_linestring_coords_lonlat([(u, v, k)], G)
            if len(edge_coords) >= 2:
                flooded_multi_coords.append(edge_coords)

    props = {
        "route_type": route_type,
        "distance_m": round(distance_m, 2),
        "eta_s": round(travel_time_s, 1),
        "num_nodes": len(route_nodes),
        "num_edges": len(route_edges),
        "origin_node": int(origin_node),
        "dest_node": int(dest_node),
        "has_flood": has_any_flood,
        "flooded_distance_m": round(flooded_distance_m, 2),
        "flooded_segments_count": len(flooded_edge_list),
        "flood_time": flood_time,
        "debug_seconds": {
            "traffic_apply": round(t_traffic, 3),
            "flood_apply": round(t_flood, 3),
            "shortest_path": round(t_path, 3),
            "total": round(time.perf_counter() - t_start, 3),
        }
    }

    # Main route feature
    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": props
    }
    
    features = [feature]
    
    # Add flooded segments as separate feature (using MultiLineString for non-contiguous segments)
    if flooded_multi_coords:
        flooded_feature = {
            "type": "Feature",
            "geometry": {"type": "MultiLineString", "coordinates": flooded_multi_coords},
            "properties": {
                "segment_type": "flooded_passable",
                "distance_m": round(flooded_distance_m, 2),
                "route_type": route_type,
                "segments_count": len(flooded_multi_coords)
            }
        }
        features.append(flooded_feature)

    result = {"type": "FeatureCollection", "features": features, "properties": props}
    
    # PROGRESSIVE CACHE: Store this result for future requests
    # Implement simple LRU: if cache full, remove oldest entry (first inserted)
    if len(_route_cache) >= MAX_ROUTE_CACHE_SIZE:
        # Remove the first (oldest) item
        oldest_key = next(iter(_route_cache))
        del _route_cache[oldest_key]
        print(f"[Cache] Evicted oldest entry (cache at max size: {MAX_ROUTE_CACHE_SIZE})")
    
    _route_cache[cache_key] = result
    print(f"[Cache] Stored new route (cache size: {len(_route_cache)})")
    
    return result


def get_graph_info() -> Dict[str, Any]:
    try:
        G = load_graph()
        return {
            "loaded": True,
            "graphml_path": str(_graphml_path_used) if _graphml_path_used else None,
            "roads_geojson_path": str(_roads_geojson_path_used) if _roads_geojson_path_used else None,
            "nodes": G.number_of_nodes(),
            "edges": G.number_of_edges(),
            "osmnx_available": OSMNX_AVAILABLE,
            "geopandas_available": GEOPANDAS_OK,
            "flood_cache_size": len(_flood_edge_cache),
            "flood_cache_meta": _flood_meta_cache,
        }
    except Exception as e:
        return {"loaded": False, "error": str(e)}


def get_cache_stats() -> Dict[str, Any]:
    """Return progressive route cache statistics"""
    total_requests = _route_cache_stats["hits"] + _route_cache_stats["misses"]
    hit_rate = (_route_cache_stats["hits"] / total_requests * 100) if total_requests > 0 else 0.0
    
    return {
        "cache_size": len(_route_cache),
        "max_size": MAX_ROUTE_CACHE_SIZE,
        "hits": _route_cache_stats["hits"],
        "misses": _route_cache_stats["misses"],
        "total_requests": total_requests,
        "hit_rate_percent": round(hit_rate, 2),
        "memory_efficient": len(_route_cache) < MAX_ROUTE_CACHE_SIZE
    }


def dump_route_cache_to_disk(folder: Path) -> str:
    """
    Debug tool: Writes the current in-memory route cache to a JSON file.
    """
    if not folder.exists():
        folder.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"route_cache_dump_{timestamp}.json"
    filepath = folder / filename
    
    # Convert tuple keys to strings for JSON compatibility
    export_data = {}
    for key, val in _route_cache.items():
        # key is (origin_lat, origin_lon, dest_lat, dest_lon, flood_idx, route_type)
        key_str = f"{key[0]},{key[1]}_to_{key[2]},{key[3]}_flood{key[4]}_{key[5]}"
        export_data[key_str] = val
        
    info = {
        "timestamp": timestamp,
        "cache_size": len(_route_cache),
        "stats": _route_cache_stats,
        "routes": export_data
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
        
    return str(filepath)

