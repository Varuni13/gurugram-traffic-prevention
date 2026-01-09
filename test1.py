#!/usr/bin/env python
# coding: utf-8

# In[2]:


# Cell 1: Load GraphML
import os
import networkx as nx

GRAPHML_PATH = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml"  # <-- update, example: r"data/gurugram.graphml"

print("File exists:", os.path.exists(GRAPHML_PATH), GRAPHML_PATH)

# Try loading with osmnx first (best for OSM graphs), fallback to networkx
try:
    import osmnx as ox
    G = ox.load_graphml(GRAPHML_PATH)
    loader = "osmnx.load_graphml"
except Exception as e:
    print("OSMnx load failed, trying networkx.read_graphml. Error:", e)
    G = nx.read_graphml(GRAPHML_PATH)
    loader = "networkx.read_graphml"

print("Loaded using:", loader)
print("Graph type:", type(G))
print("Directed:", G.is_directed() if hasattr(G, "is_directed") else "unknown")


# In[3]:


# Cell 2: Basic counts and connectivity
import random

num_nodes = G.number_of_nodes()
num_edges = G.number_of_edges()

print("Nodes:", num_nodes)
print("Edges:", num_edges)

# Weakly connected components (good for directed road graphs)
if hasattr(nx, "weakly_connected_components") and G.is_directed():
    comps = list(nx.weakly_connected_components(G))
    comps_sorted = sorted(comps, key=len, reverse=True)
    print("Weakly connected components:", len(comps_sorted))
    print("Largest component size:", len(comps_sorted[0]))
else:
    comps = list(nx.connected_components(G.to_undirected()))
    comps_sorted = sorted(comps, key=len, reverse=True)
    print("Connected components:", len(comps_sorted))
    print("Largest component size:", len(comps_sorted[0]))

# Quick test: pick two nodes from largest component and see if a path exists
largest_nodes = list(comps_sorted[0])
a, b = random.sample(largest_nodes, 2)
try:
    p = nx.shortest_path(G, a, b)
    print("Path test: OK. Example path length (nodes):", len(p))
except Exception as e:
    print("Path test failed:", e)


# In[4]:


# Cell 3: Inspect node attributes
sample_node = next(iter(G.nodes))
node_data = G.nodes[sample_node]

print("Sample node id:", sample_node)
print("Sample node keys:", list(node_data.keys()))

# Common coordinate keys in OSMnx graphs
coord_candidates = [("y","x"), ("lat","lon"), ("latitude","longitude")]
found = False
for latk, lonk in coord_candidates:
    if latk in node_data and lonk in node_data:
        print(f"Found coords: {latk},{lonk} =", node_data[latk], node_data[lonk])
        found = True
        break

if not found:
    print(" No obvious node coords found. Need to locate coordinate fields.")


# In[5]:


# Cell 4: Inspect edge attributes (handles MultiDiGraph)
is_multi = isinstance(G, (nx.MultiDiGraph, nx.MultiGraph))
print("Is MultiGraph:", is_multi)

# Get one edge data record
if is_multi:
    u, v, k, edata = next(iter(G.edges(keys=True, data=True)))
    print("Sample edge:", (u, v, k))
else:
    u, v, edata = next(iter(G.edges(data=True)))
    print("Sample edge:", (u, v))

print("Edge keys:", list(edata.keys()))

# Check for length
length_keys = ["length", "len", "distance", "weight"]
found_len = [k for k in length_keys if k in edata]
print("Length-like keys present:", found_len)

# Check for geometry
geom_keys = ["geometry", "wkt", "geom"]
found_geom = [k for k in geom_keys if k in edata]
print("Geometry-like keys present:", found_geom)

# Check osmid (useful for mapping)
osmid_present = "osmid" in edata
print("osmid present:", osmid_present)
if osmid_present:
    print("osmid sample:", edata["osmid"])


# In[6]:


# Cell 5: Test nearest node lookup (requires osmnx)
try:
    import osmnx as ox
    
    # pick a random node and use its coordinates as query
    n = next(iter(G.nodes))
    nd = G.nodes[n]
    
    # OSMnx uses y=lat, x=lon
    lat = nd.get("y", nd.get("lat"))
    lon = nd.get("x", nd.get("lon"))
    print("Using test coords:", lat, lon)

    nn = ox.distance.nearest_nodes(G, X=lon, Y=lat)
    print("Nearest node lookup OK. Nearest node:", nn)
except Exception as e:
    print("Nearest node lookup failed:", e)


# In[7]:


# Cell 6: Try making a small route and exporting edges as GeoDataFrame (best case)
try:
    import osmnx as ox
    import geopandas as gpd
    
    # pick two nodes in largest component
    if G.is_directed():
        comps = list(nx.weakly_connected_components(G))
    else:
        comps = list(nx.connected_components(G.to_undirected()))
    largest = max(comps, key=len)
    n1, n2 = random.sample(list(largest), 2)
    
    route_nodes = nx.shortest_path(G, n1, n2, weight="length") if "length" in edata else nx.shortest_path(G, n1, n2)
    print("Route nodes:", len(route_nodes))
    
    # Convert route to GeoDataFrame of edges
    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
    print("Edges GeoDataFrame cols:", list(gdf_edges.columns)[:20], "...")
    
    # Filter edges in route for preview
    # OSMnx has helper:
    route_gdf = ox.routing.route_to_gdf(G, route_nodes, weight="length")
    print("Route edges rows:", len(route_gdf))
    print(route_gdf.head(3))
    
except Exception as e:
    print("Route -> Geo export test failed:", e)


# In[7]:


import matplotlib.pyplot as plt

# Plot graph with OSM basemap (G is already loaded from previous cells)
fig, ax = ox.plot_graph(
    G,
    bgcolor="white",
    node_size=0,
    edge_color="#555555",
    edge_linewidth=0.8,
    show=False,
    close=False
)

plt.title("Road Network from GraphML over OSM")
plt.show()


# In[9]:


# =========================
# STEP 1: Build Fixed OD Pairs (No routing yet)
# Objective:
#   1) Read your traffic_flow_history.csv to extract coordinates for known locations.
#   2) Create the 7 OD pairs we finalized using those points.
#   3) Validate that all required locations exist and have coordinates.
#
# Why this step matters:
#   - Controlled OD pairs = stable demo, no random clicks, no missing coverage.
#   - We ensure all OD endpoints are within our study area and have traffic history.
# =========================

import pandas as pd

# ---- 1) Load monitoring points from your traffic history CSV ----
# NOTE: Your CSV appears to have no header and columns like:
# timestamp, name, lat, lon, frc, currentSpeed, freeFlowSpeed, currentTT, freeFlowTT, delay, speed_ratio, confidence
CSV_PATH = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\gurugram_traffic_prevention\collector\outputs\traffic_flow_history.csv"  # <-- adjust if needed

cols = [
    "timestamp_utc", "name", "lat", "lon", "frc",
    "currentSpeed_kmph", "freeFlowSpeed_kmph",
    "currentTravelTime_s", "freeFlowTravelTime_s",
    "delay_s", "speed_ratio", "confidence"
]

df = pd.read_csv(CSV_PATH, header=None, names=cols)

# Basic cleanup
df["name"] = df["name"].astype(str).str.strip()
df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
df["lon"] = pd.to_numeric(df["lon"], errors="coerce")

# Keep only valid coordinates
df = df.dropna(subset=["lat", "lon"])

# For each location name, take the latest seen lat/lon (in case repeated)
# This creates a dictionary: name -> (lat, lon)
points_df = (
    df.sort_values("timestamp_utc")
      .groupby("name", as_index=False)
      .tail(1)[["name", "lat", "lon"]]
      .sort_values("name")
)

points = {row["name"]: (float(row["lat"]), float(row["lon"])) for _, row in points_df.iterrows()}

print("Loaded monitoring points:", len(points))
print("Sample points:", list(points.items())[:5])

# ---- 2) Define the 7 OD pairs (names must match exactly with your points keys) ----
# Objective: Build fixed demo pairs from your monitoring locations.
OD_PAIR_NAMES = [
    ("Cyber Hub", "IFFCO Chowk"),
    ("Huda City Centre", "MG Road"),
    ("Rajiv Chowk", "IFFCO Chowk"),
    ("Golf Course Rd", "Sohna Road"),
    ("Sector 56", "Huda City Centre"),
    ("NH-48 (Ambience)", "Cyber Hub"),
    ("Manesar Rd", "NH-48 (Ambience)")
]

# ---- 3) Validate that all required OD endpoints exist in monitoring points ----
missing = []
for o, d in OD_PAIR_NAMES:
    if o not in points:
        missing.append(o)
    if d not in points:
        missing.append(d)

missing = sorted(set(missing))
if missing:
    print("\n ERROR: These OD endpoints were not found in traffic points dictionary:")
    for m in missing:
        print("  -", m)
    print("\nAvailable point names are:")
    print(sorted(points.keys()))
    raise ValueError("Missing OD endpoints. Fix name mismatch or add those points in CSV.")
else:
    print("\nAll OD endpoints found in traffic history.")

# ---- 4) Build final OD pairs dataset (lat/lon ready) ----
od_pairs = []
for idx, (o_name, d_name) in enumerate(OD_PAIR_NAMES, start=1):
    o_lat, o_lon = points[o_name]
    d_lat, d_lon = points[d_name]
    od_pairs.append({
        "id": idx,
        "origin_name": o_name,
        "origin_lat": o_lat,
        "origin_lon": o_lon,
        "dest_name": d_name,
        "dest_lat": d_lat,
        "dest_lon": d_lon
    })

# ---- 5) Print final OD pairs clearly (this is your Step-1 deliverable) ----
print("\n====================")
print("FINAL 7 OD PAIRS")
print("====================")
for p in od_pairs:
    print(
        f'{p["id"]}. {p["origin_name"]} ({p["origin_lat"]:.6f},{p["origin_lon"]:.6f})'
        f'  -->  {p["dest_name"]} ({p["dest_lat"]:.6f},{p["dest_lon"]:.6f})'
    )

# Optional: store to a JSON file so frontend/backend can reuse the same source later
OUT_JSON = r"collector/outputs/od_pairs.json"
pd.DataFrame(od_pairs).to_json(OUT_JSON, orient="records", indent=2)
print(f"\n Saved OD pairs to: {OUT_JSON}")


# In[10]:


# =========================
# STEP 2: Load GraphML + Mandatory Network Checks
# Objective:
#   1) Load the GraphML road network (ggn_extent.graphml)
#   2) Confirm it's usable for routing: connected, has coords, has edge lengths
#   3) Produce a repeatable summary we will rely on in later steps
# =========================

import os
import networkx as nx

GRAPHML_PATH = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml"  # <-- keep your correct path

print("File exists:", os.path.exists(GRAPHML_PATH))

# Load using OSMnx (best for OSM-derived graphs)
import osmnx as ox
G = ox.load_graphml(GRAPHML_PATH)

print("\nGraph loaded successfully")
print("Graph type:", type(G))
print("Directed:", G.is_directed())
print("MultiGraph:", isinstance(G, (nx.MultiDiGraph, nx.MultiGraph)))

# Basic counts
print("\nNodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())

# Connectivity check (for directed road graphs use weakly connected components)
wcc = list(nx.weakly_connected_components(G))
wcc_sorted = sorted(wcc, key=len, reverse=True)
print("\nWeakly connected components:", len(wcc_sorted))
print("Largest component size:", len(wcc_sorted[0]))

# Sample node attribute check (coords must exist)
sample_node = next(iter(G.nodes))
node_data = G.nodes[sample_node]
print("\nSample node id:", sample_node)
print("Sample node keys:", list(node_data.keys()))
print("Sample node (lat,lon) = (y,x):", node_data.get("y"), node_data.get("x"))

# Sample edge attribute check (length must exist)
u, v, k, edata = next(iter(G.edges(keys=True, data=True)))
print("\nSample edge (u,v,key):", (u, v, k))
print("Sample edge keys:", list(edata.keys()))
print("Has 'length'?", "length" in edata, "  length value:", edata.get("length"))

print("\nSTEP-2 checks complete.")


# In[11]:


# =========================
# FIX OD #7 (Manesar) by moving it inside graph extent
# Objective:
#   Replace OD #7 origin coordinate (Manesar Rd) with the snapped node coordinate
#   so snap distance becomes near 0 and routing becomes stable.
# =========================

import json

OD_JSON_PATH = r"collector/outputs/od_pairs.json"
SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"

# Load original OD pairs
with open(OD_JSON_PATH, "r", encoding="utf-8") as f:
    od_pairs = json.load(f)

# Load snapped results (from Step-3) to reuse the snapped node coordinates
with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

# Find OD pair id=7 in snapped file
p7 = next((p for p in snapped if p["id"] == 7), None)
if not p7:
    raise ValueError("Could not find id=7 in od_pairs_snapped.json")

# Extract snapped node lat/lon for origin of OD #7
# Note: in your snapped output, we stored origin_node_latlon as a string,
# but we can use the node id to get y/x directly from G to be safest.
o_node = p7["origin_node"]
o_node_lat = float(G.nodes[o_node]["y"])
o_node_lon = float(G.nodes[o_node]["x"])

print("Old Manesar origin:", [p["origin_lat"] for p in od_pairs if p["id"] == 7][0],
      [p["origin_lon"] for p in od_pairs if p["id"] == 7][0])

print("New Manesar origin (inside graph):", o_node_lat, o_node_lon)

# Update OD pair #7 in od_pairs.json
for p in od_pairs:
    if p["id"] == 7:
        p["origin_lat"] = o_node_lat
        p["origin_lon"] = o_node_lon
        # Optional rename to be clear in demo
        p["origin_name"] = "Manesar Rd (within extent)"
        break

# Save updated OD pairs
with open(OD_JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(od_pairs, f, indent=2)



# In[12]:


# =========================
# STEP 3 (Re-run after fixing OD #7): Confirm snapping is correct
# Objective:
#   1) Reload updated od_pairs.json
#   2) Snap all 7 OD pairs to nearest graph nodes again
#   3) Print snap distances (meters) to confirm OD #7 is now near 0
# =========================

import json
import pandas as pd
import osmnx as ox
from geopy.distance import distance
import networkx as nx

# Ensure graph is loaded
if 'G' not in locals():
    GRAPHML_PATH = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml"
    G = ox.load_graphml(GRAPHML_PATH)
    print("Graph loaded in this cell")

OD_JSON_PATH = r"collector/outputs/od_pairs.json"

# --- Load updated OD pairs ---
with open(OD_JSON_PATH, "r", encoding="utf-8") as f:
    od_pairs = json.load(f)

print("Loaded OD pairs:", len(od_pairs))

rows = []
for p in od_pairs:
    o_lat, o_lon = p["origin_lat"], p["origin_lon"]
    d_lat, d_lon = p["dest_lat"], p["dest_lon"]

    # Snap to nearest nodes
    o_node = ox.distance.nearest_nodes(G, X=o_lon, Y=o_lat)
    d_node = ox.distance.nearest_nodes(G, X=d_lon, Y=d_lat)

    # Node coordinates
    o_node_lat, o_node_lon = G.nodes[o_node]["y"], G.nodes[o_node]["x"]
    d_node_lat, d_node_lon = G.nodes[d_node]["y"], G.nodes[d_node]["x"]

    # Snap distance in meters (point -> snapped node)
    o_snap_m = float(distance((o_lat, o_lon), (o_node_lat, o_node_lon)).meters)
    d_snap_m = float(distance((d_lat, d_lon), (d_node_lat, d_node_lon)).meters)

    rows.append({
        "id": p["id"],
        "origin_name": p["origin_name"],
        "origin_latlon": f"{o_lat:.6f},{o_lon:.6f}",
        "origin_node": o_node,
        "origin_node_latlon": f"{o_node_lat:.6f},{o_node_lon:.6f}",
        "origin_snap_m": round(o_snap_m, 1),
        "dest_name": p["dest_name"],
        "dest_latlon": f"{d_lat:.6f},{d_lon:.6f}",
        "dest_node": d_node,
        "dest_node_latlon": f"{d_node_lat:.6f},{d_node_lon:.6f}",
        "dest_snap_m": round(d_snap_m, 1),
    })

snap_df = pd.DataFrame(rows).sort_values("id")

print("\n====================")
print("CONFIRMATION: OD -> NEAREST NODES (snap distance)")
print("====================")
print(snap_df[[
    "id",
    "origin_name", "origin_latlon", "origin_node", "origin_node_latlon", "origin_snap_m",
    "dest_name", "dest_latlon", "dest_node", "dest_node_latlon", "dest_snap_m"
]].to_string(index=False))

# Optional: save updated snapped file for later steps
OUT_PATH = r"collector/outputs/od_pairs_snapped.json"
with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(rows, f, indent=2)

print(f"\nSaved updated snapped OD pairs to: {OUT_PATH}")

# Extra quick check just for OD #7
od7 = snap_df[snap_df["id"] == 7]
if not od7.empty:
    print("\n OD #7 snap distances:",
          "origin_snap_m =", float(od7["origin_snap_m"].iloc[0]),
          "| dest_snap_m =", float(od7["dest_snap_m"].iloc[0]))


# In[13]:


# =========================
# STEP 3A: Visualize Graph + OD pairs on Folium
# Objective:
#   Sanity-check that:
#   1) GraphML roads align with the basemap
#   2) OD points lie inside the study area
#   3) We can visually spot outliers (like Manesar)
#
# Output:
#   An interactive Folium map in the notebook.
# =========================

import json
import folium
import osmnx as ox
from shapely.geometry import mapping

# ---- Load snapped OD pairs (from Step-3) ----
SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"
with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

# ---- Convert graph edges to GeoDataFrame for plotting ----
# This gives us 'geometry' for edges for clean visualization.
gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)

# ---- Center map: use average of all OD points ----
# Parse origin_latlon and dest_latlon strings (format: "lat,lon")
all_lats = []
all_lons = []
for p in snapped:
    o_lat, o_lon = map(float, p["origin_latlon"].split(","))
    d_lat, d_lon = map(float, p["dest_latlon"].split(","))
    all_lats.extend([o_lat, d_lat])
    all_lons.extend([o_lon, d_lon])

center_lat = sum(all_lats) / len(all_lats)
center_lon = sum(all_lons) / len(all_lons)

m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

# ---- Add road network edges (GeoJSON layer) ----
# Keep properties minimal to reduce load.
edges_geojson = {
    "type": "FeatureCollection",
    "features": []
}

for (_, row) in gdf_edges.reset_index().iterrows():
    geom = row["geometry"]
    if geom is None:
        continue
    edges_geojson["features"].append({
        "type": "Feature",
        "geometry": mapping(geom),
        "properties": {"length": float(row.get("length", 0.0))}
    })

for p in snapped:
    oid = p["id"]
    o_name = p["origin_name"]
    d_name = p["dest_name"]

    # Parse origin and destination coordinates from latlon strings
    o_lat, o_lon = map(float, p["origin_latlon"].split(","))
    d_lat, d_lon = map(float, p["dest_latlon"].split(","))

    o_snap = p["origin_snap_m"]
    d_snap = p["dest_snap_m"]

    # Mark Manesar outlier (large snap) in orange
    origin_color = "orange" if o_snap > 500 else "green"

    # Origin marker
    folium.Marker(
        location=[o_lat, o_lon],
        popup=f"OD {oid} ORIGIN: {o_name}<br>Snap: {o_snap} m",
        icon=folium.Icon(color=origin_color, icon="play")
    ).add_to(m)

    # Destination marker
    folium.Marker(
        location=[d_lat, d_lon],
        popup=f"OD {oid} DEST: {d_name}<br>Snap: {d_snap} m",
        icon=folium.Icon(color="red", icon="stop")
    ).add_to(m)

    # Dashed line between origin and destination (just for reference)
    folium.PolyLine(
        locations=[[o_lat, o_lon], [d_lat, d_lon]],
        color="#0000FF",
        weight=2,
        opacity=0.6,
        dash_array="6, 6",
        tooltip=f"OD {oid}: {o_name} -> {d_name}"
    ).add_to(m)

folium.LayerControl().add_to(m)

m.save("map.html")



# In[14]:


# =========================
# STEP 4: Baseline routing (distance-only)
# Objective:
#   Compute shortest (by distance) route for each OD pair using GraphML edge length.
#   This baseline is needed to compare against traffic-aware routing later.
# =========================

import json
import networkx as nx

SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"
OUT_BASELINE = r"collector/outputs/baseline_routes.json"

# --- Load snapped OD pairs (node ids already computed) ---
with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

print(" Loaded snapped OD pairs:", len(snapped))

baseline_results = []

for p in snapped:
    pid = p["id"]
    o_node = p["origin_node"]
    d_node = p["dest_node"]
    label = f'{pid}. {p["origin_name"]} -> {p["dest_name"]}'

    try:
        # Shortest path by length (meters)
        route_nodes = nx.shortest_path(G, o_node, d_node, weight="length")

        # Calculate total route length by summing edge lengths along the path
        # Note: MultiDiGraph can have multiple edges; we'll take the minimum-length edge between consecutive nodes
        total_len_m = 0.0
        edge_list = []

        for u, v in zip(route_nodes[:-1], route_nodes[1:]):
            # G[u][v] returns dict of keys -> edge attrs
            candidates = G[u][v]
            # pick the edge key with minimum length
            best_key = min(candidates, key=lambda k: candidates[k].get("length", float("inf")))
            best_edge = candidates[best_key]
            seg_len = float(best_edge.get("length", 0.0))
            total_len_m += seg_len
            edge_list.append({"u": u, "v": v, "key": best_key, "length_m": seg_len})

        baseline_results.append({
            "id": pid,
            "pair": label,
            "origin_node": o_node,
            "dest_node": d_node,
            "route_nodes": route_nodes,
            "route_edges": edge_list,
            "distance_m": total_len_m,
            "distance_km": round(total_len_m / 1000.0, 3),
            "status": "OK"
        })

        print(f"{label} | distance={total_len_m/1000:.3f} km | edges={len(edge_list)}")

    except Exception as e:
        baseline_results.append({
            "id": pid,
            "pair": label,
            "origin_node": o_node,
            "dest_node": d_node,
            "status": f"FAILED: {str(e)}"
        })
        print(f"{label} | FAILED:", e)

# --- Save baseline routes for next steps ---
with open(OUT_BASELINE, "w", encoding="utf-8") as f:
    json.dump(baseline_results, f, indent=2)

print("\nSaved baseline routes to:", OUT_BASELINE)


# In[15]:


# =========================
# STEP 4A: Diagnose why OD #7 has "No path"
# Objective:
#   Check if a path exists in:
#     1) directed graph (legal one-way)
#     2) undirected graph (ignore one-way)
#   and inspect degrees of origin/destination nodes.
# =========================

import json
import networkx as nx

SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"

with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

p7 = next(p for p in snapped if p["id"] == 7)
o = p7["origin_node"]
d = p7["dest_node"]

print("OD #7:", p7["origin_name"], "->", p7["dest_name"])
print("Origin node:", o, " Dest node:", d)

print("\n--- Degree info (directed graph) ---")
print("Origin out_degree:", G.out_degree(o), " in_degree:", G.in_degree(o))
print("Dest   out_degree:", G.out_degree(d), " in_degree:", G.in_degree(d))

print("\n--- Path existence ---")
print("Directed has path?", nx.has_path(G, o, d))

G_und = G.to_undirected()
print("Undirected has path?", nx.has_path(G_und, o, d))


# In[18]:


# =========================
# STEP 4B: Auto-fix OD #7 start node (directed routing issue)
# Objective:
#   OD #7 origin node has out_degree=0 (can't move forward).
#   We will search the 30 nearest nodes to the Manesar coordinate and pick
#   the first node that:
#     1) has out_degree > 0
#     2) can reach destination in the directed graph (nx.has_path == True)
#   Then we update od_pairs_snapped.json with the fixed origin_node.
# =========================

import json
import networkx as nx
import osmnx as ox
import pandas as pd
from geopy.distance import distance

SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"

# --- Load snapped OD pairs ---
with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

# --- Get OD #7 ---
p7 = next((p for p in snapped if p["id"] == 7), None)
if not p7:
    raise ValueError("OD #7 not found in od_pairs_snapped.json")

# Parse origin_latlon string (format: "lat,lon")
o_lat, o_lon = map(float, p7["origin_latlon"].split(","))
d_node = p7["dest_node"]
bad_origin_node = p7["origin_node"]

print("OD #7:", p7["origin_name"], "->", p7["dest_name"])
print("Current origin_node:", bad_origin_node,
      "| out_degree:", G.out_degree(bad_origin_node),
      "| in_degree:", G.in_degree(bad_origin_node))
print("Destination node:", d_node)
print("Directed has path currently?", nx.has_path(G, bad_origin_node, d_node))
# --- Build candidates: 30 nearest nodes to OD7 origin coordinate ---
# (We use node GeoDataFrame + haversine distance in meters)
import numpy as np

gdf_nodes = ox.graph_to_gdfs(G, nodes=True, edges=False)

# Haversine distance formula (fast vectorized computation)
def haversine_distance(lat1, lon1, lats, lons):
    """Calculate distance in meters between point (lat1,lon1) and arrays of points"""
    R = 6371000  # Earth radius in meters
    
    lat1_rad = np.radians(lat1)
    lats_rad = np.radians(lats)
    delta_lat = np.radians(lats - lat1)
    delta_lon = np.radians(lons - lon1)
    
    a = np.sin(delta_lat/2)**2 + np.cos(lat1_rad) * np.cos(lats_rad) * np.sin(delta_lon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    return R * c

gdf_nodes = gdf_nodes.copy()
gdf_nodes["dist_m"] = haversine_distance(
    o_lat, o_lon,
    gdf_nodes["y"].values,
    gdf_nodes["x"].values
)


K = 30
candidates = gdf_nodes.nsmallest(K, "dist_m")

print(f"\nSearching among {K} nearest nodes...")

# --- Pick the first node that is routable in directed graph ---
fixed_node = None
for node_id, row in candidates.iterrows():
    node_id = int(node_id)

    # Must be a place you can leave from
    if G.out_degree(node_id) <= 0:
        continue

    # Must be able to reach destination with directed edges
    if nx.has_path(G, node_id, d_node):
        fixed_node = node_id
        fixed_dist = float(row["dist_m"])
        break

if not fixed_node:
    print("\n No suitable node found in the nearest", K, "nodes.")
    print("Try increasing K to 100, or we will use fallback strategy.")
    raise ValueError("Auto-fix failed: no reachable nearby origin node found.")

# --- Update OD #7 in snapped dataset ---
p7["origin_node"] = fixed_node
p7["origin_node_latlon"] = f'{G.nodes[fixed_node]["y"]:.6f},{G.nodes[fixed_node]["x"]:.6f}'
p7["origin_snap_m"] = round(fixed_dist, 1)

# Save updated snapped file
with open(SNAPPED_PATH, "w", encoding="utf-8") as f:
    json.dump(snapped, f, indent=2)

print("\n FIX APPLIED!")
print("New origin_node:", fixed_node,
      "| out_degree:", G.out_degree(fixed_node),
      "| in_degree:", G.in_degree(fixed_node))
print("New origin snap distance (m):", round(fixed_dist, 1))
print("Directed has path now?", nx.has_path(G, fixed_node, d_node))
print("\nUpdated file:", SNAPPED_PATH)


# In[19]:


import json, networkx as nx

SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"
with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

p7 = next(p for p in snapped if p["id"] == 7)
print("OD7 origin_node:", p7["origin_node"])
print("OD7 dest_node:", p7["dest_node"])
print("Directed has path?", nx.has_path(G, p7["origin_node"], p7["dest_node"]))
print("OD7 origin_snap_m:", p7.get("origin_snap_m"))


# In[20]:


# =========================
# STEP 5D: Densify route geometry (smooth visualization)
# Objective:
#   Add intermediate points along each edge geometry every N meters
#   so the plotted route follows curves smoothly.
# =========================

import math
import json
import folium
import osmnx as ox
import pandas as pd
from geopy.distance import distance

# Load the baseline routes and snapped OD pairs to extract route data
SNAPPED_PATH = r"collector/outputs/od_pairs_snapped.json"
OUT_BASELINE = r"collector/outputs/baseline_routes.json"

with open(OUT_BASELINE, "r", encoding="utf-8") as f:
    baseline_results = json.load(f)

with open(SNAPPED_PATH, "r", encoding="utf-8") as f:
    snapped = json.load(f)

# Select which OD pair to plot (1-7)
id_to_plot = 1  # Change this to 1-7 to plot different routes

# Get the route object and corresponding OD object
route_obj = next((r for r in baseline_results if r["id"] == id_to_plot), None)
od_obj_snapped = next((s for s in snapped if s["id"] == id_to_plot), None)

if not route_obj or not od_obj_snapped:
    raise ValueError(f"Could not find OD pair {id_to_plot}")

# Build od_obj from snapped data (latitude, longitude format)
o_lat, o_lon = map(float, od_obj_snapped["origin_latlon"].split(","))
d_lat, d_lon = map(float, od_obj_snapped["dest_latlon"].split(","))

od_obj = {
    "origin_name": od_obj_snapped["origin_name"],
    "origin_lat": o_lat,
    "origin_lon": o_lon,
    "dest_name": od_obj_snapped["dest_name"],
    "dest_lat": d_lat,
    "dest_lon": d_lon
}

pair_name = route_obj["pair"]
route_edges = route_obj["route_edges"]

gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

step_m = 15  # add a point every 15 meters (try 10/15/20)
route_coords_lonlat = []

def densify_linestring(coords_lonlat, step_m=15):
    """coords_lonlat is list of (lon,lat). Return densified list of (lon,lat)."""
    densified = [coords_lonlat[0]]
    for a, b in zip(coords_lonlat[:-1], coords_lonlat[1:]):
        lon1, lat1 = a
        lon2, lat2 = b
        seg_len = float(distance((lat1, lon1), (lat2, lon2)).meters)
        if seg_len <= step_m:
            densified.append(b)
            continue
        # number of interior points
        n = int(seg_len // step_m)
        for i in range(1, n + 1):
            t = i / (n + 1)
            lon = lon1 + (lon2 - lon1) * t
            lat = lat1 + (lat2 - lat1) * t
            densified.append((lon, lat))
        densified.append(b)
    return densified

# Build densified route coords
for i, e in enumerate(route_edges):
    u = int(e["u"]); v = int(e["v"]); k = int(e["key"])
    geom = gdf_edges.loc[(u, v, k)].geometry
    coords = list(geom.coords)  # (lon,lat)

    coords = densify_linestring(coords, step_m=step_m)

    if i == 0:
        route_coords_lonlat.extend(coords)
    else:
        # avoid duplicate join point
        if route_coords_lonlat[-1] == coords[0]:
            route_coords_lonlat.extend(coords[1:])
        else:
            route_coords_lonlat.extend(coords)

route_coords_latlon = [[lat, lon] for lon, lat in route_coords_lonlat]

# Plot
o_lat, o_lon = od_obj["origin_lat"], od_obj["origin_lon"]
d_lat, d_lon = od_obj["dest_lat"], od_obj["dest_lon"]
center_lat = (o_lat + d_lat) / 2
center_lon = (o_lon + d_lon) / 2

m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")

folium.Marker([o_lat, o_lon], popup=f"Origin: {od_obj['origin_name']}",
              icon=folium.Icon(color="green", icon="play")).add_to(m)
folium.Marker([d_lat, d_lon], popup=f"Destination: {od_obj['dest_name']}",
              icon=folium.Icon(color="red", icon="stop")).add_to(m)

folium.PolyLine(
    route_coords_latlon,
    weight=5,
    opacity=0.9,
    tooltip=f"{pair_name} | {route_obj['distance_km']} km | densified {step_m}m"
).add_to(m)

m


# In[21]:


# =========================
# STEP 5 Debug: Find "jump" segments in the plotted route
# Objective:
#   Identify if route has:
#    - missing geometry edges (fallback straight lines)
#    - unusually large coordinate jumps between consecutive points
# =========================

from geopy.distance import distance
import numpy as np

# Helper function to calculate great circle distance
def haversine_distance_m(lat1, lon1, lat2, lon2):
    """Calculate distance in meters between two points using haversine formula"""
    return float(distance((lat1, lon1), (lat2, lon2)).meters)

# route_edges and route_coords_lonlat must exist from Step-5
# route_coords_lonlat is [(lon,lat), ...]

# 1) Check missing-geometry count
missing_geom_edges = []
for e in route_edges:
    u = int(e["u"]); v = int(e["v"]); k = int(e["key"])
    edata = G.get_edge_data(u, v, k)
    if edata is None or edata.get("geometry", None) is None:
        missing_geom_edges.append((u, v, k, e.get("length_m")))

print("Missing-geometry edges:", len(missing_geom_edges))
if missing_geom_edges:
    print("Sample missing geometry edges (u,v,key,length_m):")
    print(missing_geom_edges[:10])

# 2) Check large jumps between consecutive coordinates in the final polyline
jump_threshold_m = 80  # you can tune, 80m is a strong indicator at city zoom
jumps = []

for i in range(1, len(route_coords_lonlat)):
    lon1, lat1 = route_coords_lonlat[i-1]
    lon2, lat2 = route_coords_lonlat[i]
    dist_m = haversine_distance_m(lat1, lon1, lat2, lon2)
    if dist_m > jump_threshold_m:
        jumps.append((i, dist_m, (lat1, lon1), (lat2, lon2)))

print("\nCoordinate jumps >", jump_threshold_m, "m:", len(jumps))
if jumps:
    print("Top 10 jumps (index, meters, from, to):")
    for j in jumps[:10]:
        print(j)


# In[22]:


# =========================
# STEP 6: Prepare latest traffic snapshot (TomTom-derived)
# Objective:
#   1) Load traffic history CSV
#   2) For each location, take the latest record
#   3) Compute speed_ratio if missing
#   4) Validate and save a clean snapshot for Step-7 (edge mapping)
# =========================

import pandas as pd
import numpy as np
import json

CSV_PATH = r"collector/outputs/traffic_flow_history.csv"
OUT_SNAPSHOT = r"collector/outputs/traffic_snapshot_latest.json"

cols = [
    "timestamp_utc", "name", "lat", "lon", "frc",
    "currentSpeed_kmph", "freeFlowSpeed_kmph",
    "currentTravelTime_s", "freeFlowTravelTime_s",
    "delay_s", "speed_ratio", "confidence"
]

df = pd.read_csv(CSV_PATH, header=None, names=cols)

# Clean + types
df["name"] = df["name"].astype(str).str.strip()
for c in ["lat","lon","currentSpeed_kmph","freeFlowSpeed_kmph","speed_ratio","confidence"]:
    df[c] = pd.to_numeric(df[c], errors="coerce")

df = df.dropna(subset=["name","lat","lon","currentSpeed_kmph","freeFlowSpeed_kmph"])

# Take latest record per location (by timestamp string)
latest = (
    df.sort_values("timestamp_utc")
      .groupby("name", as_index=False)
      .tail(1)
      .reset_index(drop=True)
)

# Compute speed_ratio if missing or invalid
latest["speed_ratio_calc"] = latest["currentSpeed_kmph"] / latest["freeFlowSpeed_kmph"]
latest["speed_ratio_final"] = latest["speed_ratio"]
mask_bad = latest["speed_ratio_final"].isna() | (latest["speed_ratio_final"] <= 0)
latest.loc[mask_bad, "speed_ratio_final"] = latest.loc[mask_bad, "speed_ratio_calc"]

# Clamp to a reasonable range (optional but safe)
latest["speed_ratio_final"] = latest["speed_ratio_final"].clip(lower=0, upper=2)

print("Traffic points (latest per location):", len(latest))
print("\nSample (5):")
print(
    latest[["name","timestamp_utc","lat","lon","currentSpeed_kmph","freeFlowSpeed_kmph","speed_ratio_final","confidence"]]
    .head(5)
    .to_string(index=False)
)

# Save as clean JSON list
snapshot = []
for _, r in latest.iterrows():
    snapshot.append({
        "name": r["name"],
        "timestamp_utc": r["timestamp_utc"],
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "currentSpeed_kmph": float(r["currentSpeed_kmph"]),
        "freeFlowSpeed_kmph": float(r["freeFlowSpeed_kmph"]),
        "speed_ratio": float(r["speed_ratio_final"]),
        "confidence": None if pd.isna(r["confidence"]) else float(r["confidence"])
    })

with open(OUT_SNAPSHOT, "w", encoding="utf-8") as f:
    json.dump({"count": len(snapshot), "points": snapshot}, f, indent=2)

print("\nSaved traffic snapshot to:", OUT_SNAPSHOT)

# Quick sanity range check
print("\nSpeed ratio stats:")
print("min:", float(np.min(latest["speed_ratio_final"])))
print("max:", float(np.max(latest["speed_ratio_final"])))
print("mean:", float(np.mean(latest["speed_ratio_final"])))


# In[23]:


# =========================
# STEP 7: Map traffic monitoring points -> nearest road edges
# Objective:
#   1) Load traffic_snapshot_latest.json (10 points)
#   2) For each point, find nearest graph edge (u,v,key)
#   3) Save mapping: point_name -> (u,v,key) + speed_ratio
# =========================

import json
import osmnx as ox
import pandas as pd

SNAPSHOT_PATH = r"collector/outputs/traffic_snapshot_latest.json"
OUT_EDGE_MAP  = r"collector/outputs/traffic_points_to_edges.json"

# 1) Load snapshot
with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
    snap = json.load(f)

points = snap["points"]
print("Loaded traffic points:", len(points))

# 2) Convert to DataFrame
df = pd.DataFrame(points)

# Ensure the routing graph G is available; load it if missing
if "G" not in globals():
    # Try to reuse GRAPHML_PATH from earlier cells if present
    graph_path = globals().get("GRAPHML_PATH", None)
    if not graph_path:
        raise RuntimeError(
            "Graph 'G' not found in notebook globals and GRAPHML_PATH is not set. "
            "Define GRAPHML_PATH (path to your .graphml) and load the graph in a prior cell, e.g.:\n"
            "import osmnx as ox\nG = ox.load_graphml(GRAPHML_PATH)"
        )
    print("Graph 'G' not found, loading from:", graph_path)
    try:
        G = ox.load_graphml(graph_path)
        print(f"Loaded graph G: nodes={G.number_of_nodes()}, edges={G.number_of_edges()}")
    except Exception as e:
        raise RuntimeError(f"Failed to load graph from {graph_path}: {e}")

# 3) Find nearest edge for each point
# NOTE: OSMnx expects X = longitude, Y = latitude
try:
    nearest_edges = ox.distance.nearest_edges(
        G,
        X=df["lon"].tolist(),
        Y=df["lat"].tolist()
    )
except Exception as e:
    # In case of API differences across OSMnx versions, fall back to per-point lookup
    print("ox.distance.nearest_edges failed, falling back to per-point lookup. Error:", e)
    nearest_edges = []
    for lon, lat in zip(df["lon"].tolist(), df["lat"].tolist()):
        nearest_edges.append(ox.distance.nearest_edges(G, X=lon, Y=lat))

# nearest_edges returns list of (u,v,key)
df["nearest_u"] = [int(e[0]) for e in nearest_edges]
df["nearest_v"] = [int(e[1]) for e in nearest_edges]
df["nearest_key"] = [int(e[2]) for e in nearest_edges]

# 4) Save mapping
mapping = []
for _, r in df.iterrows():
    mapping.append({
        "name": r["name"],
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "speed_ratio": float(r["speed_ratio"]),
        "currentSpeed_kmph": float(r["currentSpeed_kmph"]),
        "freeFlowSpeed_kmph": float(r["freeFlowSpeed_kmph"]),
        "edge": [int(r["nearest_u"]), int(r["nearest_v"]), int(r["nearest_key"])]
    })

with open(OUT_EDGE_MAP, "w", encoding="utf-8") as f:
    json.dump({"count": len(mapping), "mapping": mapping}, f, indent=2)

print("\nSaved traffic point -> edge mapping to:", OUT_EDGE_MAP)

# 5) Print sample mappings
print("\nSample mappings (first 5):")
print(df[["name","speed_ratio","nearest_u","nearest_v","nearest_key"]].head(5).to_string(index=False))


# In[24]:


# =========================
# STEP 7B: Visualize traffic point -> nearest edge mapping
# Objective:
#   Show each traffic monitoring point and its mapped nearest road edge on a map.
#   This is a sanity check before using traffic weights for rerouting.
# =========================

import json
import folium
import osmnx as ox
from shapely.geometry import LineString

EDGE_MAP_PATH = r"collector/outputs/traffic_points_to_edges.json"

# 1) Load mapping
with open(EDGE_MAP_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

mapping = data["mapping"]
print("Loaded mappings:", len(mapping))

# 2) Create map centered around average of all points
avg_lat = sum(m["lat"] for m in mapping) / len(mapping)
avg_lon = sum(m["lon"] for m in mapping) / len(mapping)

m = folium.Map(location=[avg_lat, avg_lon], zoom_start=12, tiles="OpenStreetMap")

# Helper: color by speed ratio
def color_by_speed_ratio(sr: float) -> str:
    if sr >= 0.85:
        return "green"   # mostly free-flow
    elif sr >= 0.65:
        return "orange"  # moderate congestion
    else:
        return "red"     # heavy congestion

# 3) Add markers + edges
for item in mapping:
    name = item["name"]
    lat = item["lat"]
    lon = item["lon"]
    sr  = item["speed_ratio"]
    u, v, k = item["edge"]

    # Traffic point marker
    folium.CircleMarker(
        location=[lat, lon],
        radius=7,
        color=color_by_speed_ratio(sr),
        fill=True,
        fill_opacity=0.8,
        popup=(
            f"<b>{name}</b><br>"
            f"speed_ratio: {sr:.3f}<br>"
            f"currentSpeed: {item['currentSpeed_kmph']} km/h<br>"
            f"freeFlow: {item['freeFlowSpeed_kmph']} km/h<br>"
            f"edge: ({u},{v},{k})"
        )
    ).add_to(m)

    # Edge geometry from the graph
    edata = G.get_edge_data(u, v, k)
    if edata and "geometry" in edata and edata["geometry"] is not None:
        coords = list(edata["geometry"].coords)  # (lon,lat)
        edge_latlon = [(c[1], c[0]) for c in coords]
    else:
        # fallback: draw line between nodes
        edge_latlon = [(G.nodes[u]["y"], G.nodes[u]["x"]), (G.nodes[v]["y"], G.nodes[v]["x"])]

    # Draw the mapped road edge segment (highlight)
    folium.PolyLine(
        locations=edge_latlon,
        weight=7,
        opacity=0.8,
        tooltip=f"{name} mapped edge",
    ).add_to(m)

    # Optional: connector line (point -> midpoint of edge)
    mid = edge_latlon[len(edge_latlon)//2]
    folium.PolyLine(
        locations=[[lat, lon], list(mid)],
        weight=2,
        opacity=0.6,
        dash_array="5,6"
    ).add_to(m)

m


# In[25]:


# =========================
# STEP 8: Traffic-aware routing (reroute using TomTom speed_ratio)
# Objective:
#   1) Load traffic point -> edge mapping
#   2) Build edge penalty: traffic_cost = length / speed_ratio
#   3) Compute new route for each OD pair using traffic_cost
#   4) Compare baseline vs traffic-aware routes
# =========================

import json
import networkx as nx

SNAPPED_OD_PATH = r"collector/outputs/od_pairs_snapped.json"
TRAFFIC_EDGE_MAP_PATH = r"collector/outputs/traffic_points_to_edges.json"
OUT_TRAFFIC_ROUTES = r"collector/outputs/traffic_aware_routes.json"

# 1) Load OD pairs (snapped nodes)
with open(SNAPPED_OD_PATH, "r", encoding="utf-8") as f:
    od_pairs = json.load(f)

# 2) Load traffic mapping (point -> edge with speed_ratio)
with open(TRAFFIC_EDGE_MAP_PATH, "r", encoding="utf-8") as f:
    tmap = json.load(f)

traffic_edges = {}
for item in tmap["mapping"]:
    u, v, k = item["edge"]
    sr = float(item["speed_ratio"])
    # Safety clamp
    if sr <= 0:
        sr = 1.0
    traffic_edges[(u, v, k)] = sr

print("Traffic edges with known speed_ratio:", len(traffic_edges))

# 3) Create traffic_cost attribute for every edge
# Default speed_ratio = 1.0 for edges without traffic info
for u, v, k, data in G.edges(keys=True, data=True):
    length = data.get("length", 1.0)
    sr = traffic_edges.get((u, v, k), 1.0)
    data["speed_ratio"] = sr
    data["traffic_cost"] = length / sr  # slow road => bigger cost

print("Added traffic_cost attribute to graph edges.")

# Helper to compute route distance (sum of lengths)
def route_length_m(G, route_nodes):
    total = 0.0
    for a, b in zip(route_nodes[:-1], route_nodes[1:]):
        ed = min(G.get_edge_data(a, b).values(), key=lambda x: x.get("length", 1e9))
        total += float(ed.get("length", 0.0))
    return total

# Helper to compute route traffic-cost (sum of traffic_cost)
def route_traffic_cost(G, route_nodes):
    total = 0.0
    for a, b in zip(route_nodes[:-1], route_nodes[1:]):
        ed = min(G.get_edge_data(a, b).values(), key=lambda x: x.get("traffic_cost", 1e9))
        total += float(ed.get("traffic_cost", 0.0))
    return total

# 4) Compute traffic-aware routes for all OD pairs
results = []

print("\n====================")
print("STEP 8 RESULTS (Traffic-aware routing)")
print("====================")

for p in od_pairs:
    oid = p["id"]
    oname = p["origin_name"]
    dname = p["dest_name"]
    o = int(p["origin_node"])
    d = int(p["dest_node"])

    try:
        # Baseline route (length)
        base_route = nx.shortest_path(G, o, d, weight="length")
        base_len_km = route_length_m(G, base_route) / 1000.0

        # Traffic-aware route (traffic_cost)
        traf_route = nx.shortest_path(G, o, d, weight="traffic_cost")
        traf_len_km = route_length_m(G, traf_route) / 1000.0
        traf_cost = route_traffic_cost(G, traf_route)

        changed = (base_route != traf_route)

        print(f"{oid}. {oname} -> {dname}")
        print(f"   Baseline distance: {base_len_km:.3f} km")
        print(f"   Traffic-aware distance: {traf_len_km:.3f} km")
        print(f"   Traffic-aware total cost: {traf_cost:.1f}")
        print(f"   Route changed? {changed}")

        results.append({
            "id": oid,
            "origin_name": oname,
            "dest_name": dname,
            "origin_node": o,
            "dest_node": d,
            "baseline_route_nodes": base_route,
            "baseline_distance_km": round(base_len_km, 3),
            "traffic_route_nodes": traf_route,
            "traffic_distance_km": round(traf_len_km, 3),
            "traffic_total_cost": round(traf_cost, 1),
            "route_changed": changed
        })

    except Exception as e:
        print(f"{oid}. {oname} -> {dname} | FAILED:", str(e))
        results.append({
            "id": oid,
            "origin_name": oname,
            "dest_name": dname,
            "error": str(e)
        })

# 5) Save results
with open(OUT_TRAFFIC_ROUTES, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved traffic-aware routes to:", OUT_TRAFFIC_ROUTES)


# In[26]:


# =========================
# STEP 8C: Manual traffic injection test (prove rerouting works)
# Objective:
#   1) Pick one OD
#   2) Compute baseline route
#   3) Manually set one mapped traffic edge speed_ratio very low (0.2)
#   4) Compute traffic-aware route and check if it changes
# =========================

import json
import networkx as nx

SNAPPED_OD_PATH = r"collector/outputs/od_pairs_snapped.json"
TRAFFIC_EDGE_MAP_PATH = r"collector/outputs/traffic_points_to_edges.json"

TEST_OD_ID = 2        # change 1..7
FORCE_SR = 0.2        # very slow traffic for demo

# Load OD
with open(SNAPPED_OD_PATH, "r", encoding="utf-8") as f:
    ods = json.load(f)
od = next(p for p in ods if p["id"] == TEST_OD_ID)
o, d = int(od["origin_node"]), int(od["dest_node"])

print("Testing OD:", od["origin_name"], "->", od["dest_name"])

# Load traffic edges mapping
with open(TRAFFIC_EDGE_MAP_PATH, "r", encoding="utf-8") as f:
    tmap = json.load(f)

# Build dict of speed ratios
traffic_edges = {}
for item in tmap["mapping"]:
    u, v, k = item["edge"]
    traffic_edges[(int(u), int(v), int(k))] = float(item["speed_ratio"])

# Choose an edge to worsen (prefer IFFCO Chowk if exists)
edge_to_worsen = None
for item in tmap["mapping"]:
    if "IFFCO" in item["name"]:
        u, v, k = item["edge"]
        edge_to_worsen = (int(u), int(v), int(k), item["name"])
        break

if edge_to_worsen is None:
    # fallback: first traffic edge
    first = tmap["mapping"][0]
    u, v, k = first["edge"]
    edge_to_worsen = (int(u), int(v), int(k), first["name"])

u_bad, v_bad, k_bad, label = edge_to_worsen
print("Manually worsening edge for:", label, "edge:", (u_bad, v_bad, k_bad), "to speed_ratio =", FORCE_SR)

# Apply manual override
traffic_edges[(u_bad, v_bad, k_bad)] = FORCE_SR

# Update graph edge attributes
for u, v, k, data in G.edges(keys=True, data=True):
    length = float(data.get("length", 1.0))
    sr = traffic_edges.get((int(u), int(v), int(k)), 1.0)
    if sr <= 0:
        sr = 1.0
    data["traffic_cost"] = length / sr

# Compute routes
base_route = nx.shortest_path(G, o, d, weight="length")
traf_route = nx.shortest_path(G, o, d, weight="traffic_cost")

print("\nRoute changed?", base_route != traf_route)
print("Baseline nodes:", len(base_route), "| Traffic-aware nodes:", len(traf_route))


# In[27]:


# =========================
# STEP 8D: Guaranteed reroute test
# Objective:
#   1) Compute baseline route for a selected OD
#   2) Pick an edge that is actually on that baseline route
#   3) Make that edge extremely slow
#   4) Recompute route using traffic_cost and verify route changes
# =========================

import json
import networkx as nx

SNAPPED_OD_PATH = r"collector/outputs/od_pairs_snapped.json"

TEST_OD_ID = 2     # Huda City Centre -> MG Road
FORCE_SR = 0.05    # extreme congestion for demo

# Load OD
with open(SNAPPED_OD_PATH, "r", encoding="utf-8") as f:
    ods = json.load(f)
od = next(p for p in ods if p["id"] == TEST_OD_ID)

o, d = int(od["origin_node"]), int(od["dest_node"])
print("Testing OD:", od["origin_name"], "->", od["dest_name"])

# 1) Baseline route nodes
base_route = nx.shortest_path(G, o, d, weight="length")
print("Baseline nodes:", len(base_route))

# 2) Convert baseline route nodes -> list of actual edges (u,v,key) used
base_edges = []
for a, b in zip(base_route[:-1], base_route[1:]):
    # pick the shortest of possibly multiple parallel edges
    edict = G.get_edge_data(a, b)
    k_best = min(edict.keys(), key=lambda k: edict[k].get("length", 1e9))
    base_edges.append((int(a), int(b), int(k_best)))

print("Baseline edges:", len(base_edges))

# 3) Choose an edge in the middle of the route (avoid start/end)
mid_idx = len(base_edges) // 2
u_bad, v_bad, k_bad = base_edges[mid_idx]
print("Will worsen a baseline edge:", (u_bad, v_bad, k_bad), "at index", mid_idx)

# 4) Set traffic_cost on ALL edges = length (normal), then worsen only one edge
for u, v, k, data in G.edges(keys=True, data=True):
    length = float(data.get("length", 1.0))
    data["traffic_cost"] = length  # default

# Apply manual slowdown to the chosen baseline edge
edata = G.get_edge_data(u_bad, v_bad, k_bad)
if edata is None:
    raise ValueError("Chosen baseline edge not found (unexpected).")

length_bad = float(edata.get("length", 1.0))
edata["traffic_cost"] = length_bad / FORCE_SR

print(f"Applied slowdown: edge length={length_bad:.1f}m, speed_ratio={FORCE_SR}, new traffic_cost={edata['traffic_cost']:.1f}")

# 5) Compute traffic-aware route
traf_route = nx.shortest_path(G, o, d, weight="traffic_cost")

print("\nRoute changed?", base_route != traf_route)
print("Traffic-aware nodes:", len(traf_route))


# In[28]:


# =========================
# BETTER VISUALIZATION: Baseline vs Traffic-aware + Difference-only
# Objective:
#   Make both routes clearly visible even when they overlap heavily.
#   - Baseline: blue solid
#   - Traffic-aware: red dashed
#   - Difference-only segments: purple thick
# =========================

import json
import folium
import osmnx as ox
import networkx as nx

SNAPPED_OD_PATH = r"collector/outputs/od_pairs_snapped.json"
TEST_OD_ID = 2

# ---- Load OD ----
with open(SNAPPED_OD_PATH, "r", encoding="utf-8") as f:
    ods = json.load(f)
od = next(p for p in ods if p["id"] == TEST_OD_ID)

o = int(od["origin_node"])
d = int(od["dest_node"])

# Parse origin and destination from latlon strings
o_lat, o_lon = map(float, od["origin_latlon"].split(","))
d_lat, d_lon = map(float, od["dest_latlon"].split(","))

# ---- Compute routes if not already present ----
base_route = nx.shortest_path(G, o, d, weight="length")
traf_route = nx.shortest_path(G, o, d, weight="traffic_cost")

# ---- Build gdf_edges for geometry ----
gdf_edges = ox.graph_to_gdfs(G, nodes=False, edges=True)

def route_edges(route_nodes):
    """Return list of (u,v,k) edges chosen along a node route."""
    edges = []
    for a, b in zip(route_nodes[:-1], route_nodes[1:]):
        edict = G.get_edge_data(a, b)
        k_best = min(edict.keys(), key=lambda k: edict[k].get("length", 1e9))
        edges.append((int(a), int(b), int(k_best)))
    return edges

def edges_to_polyline_latlon(edge_list):
    """Convert list of edges -> continuous latlon polyline using edge geometry."""
    coords_lonlat = []
    for i, (u, v, k) in enumerate(edge_list):
        geom = gdf_edges.loc[(u, v, k)].geometry
        pts = list(geom.coords)  # (lon,lat)
        if i == 0:
            coords_lonlat.extend(pts)
        else:
            # avoid duplicate vertex
            if coords_lonlat and pts and coords_lonlat[-1] == pts[0]:
                coords_lonlat.extend(pts[1:])
            else:
                coords_lonlat.extend(pts)
    return [[lat, lon] for lon, lat in coords_lonlat]

base_edges = route_edges(base_route)
traf_edges = route_edges(traf_route)

base_latlon = edges_to_polyline_latlon(base_edges)
traf_latlon = edges_to_polyline_latlon(traf_edges)

# ---- Build difference edges (edges present in traffic route but not in baseline) ----
base_set = set(base_edges)
traf_set = set(traf_edges)
diff_edges = [e for e in traf_edges if e not in base_set]

diff_latlon = edges_to_polyline_latlon(diff_edges) if diff_edges else None

# ---- Map ----
m = folium.Map(location=[(o_lat + d_lat)/2, (o_lon + d_lon)/2], zoom_start=13, tiles="OpenStreetMap")

# Markers
folium.Marker([o_lat, o_lon], popup=f"Origin: {od['origin_name']}",
              icon=folium.Icon(color="green", icon="play")).add_to(m)
folium.Marker([d_lat, d_lon], popup=f"Destination: {od['dest_name']}",
              icon=folium.Icon(color="red", icon="stop")).add_to(m)

# Feature groups for toggles
fg_base = folium.FeatureGroup(name="Baseline (Shortest Distance)", show=True)
fg_traf = folium.FeatureGroup(name="Traffic-aware (Suggested)", show=True)
fg_diff = folium.FeatureGroup(name="Only Changed Part (Traffic route)", show=True)

# Baseline: blue solid thick
folium.PolyLine(
    base_latlon,
    color="blue",
    weight=8,
    opacity=0.8,
    tooltip="Baseline route"
).add_to(fg_base)

# Traffic-aware: red dashed, slightly thinner
folium.PolyLine(
    traf_latlon,
    color="red",
    weight=6,
    opacity=0.9,
    dash_array="10,10",
    tooltip="Traffic-aware route"
).add_to(fg_traf)

# Difference-only: purple very thick (this is the best visual helper)
if diff_latlon and len(diff_latlon) > 2:
    folium.PolyLine(
        diff_latlon,
        color="purple",
        weight=12,
        opacity=0.9,
        tooltip="Only the part that changed"
    ).add_to(fg_diff)
else:
    folium.Marker(
        [(o_lat + d_lat)/2, (o_lon + d_lon)/2],
        popup="Routes are almost identical here (very small change or overlap).",
        icon=folium.Icon(color="gray", icon="info-sign")
    ).add_to(fg_diff)

fg_base.add_to(m)
fg_traf.add_to(m)
fg_diff.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)

# Auto zoom to bounds
m.fit_bounds([ [o_lat, o_lon], [d_lat, d_lon] ])

m


# In[30]:


get_ipython().system('jupyter nbconvert --to script test1.ipynb')


# In[29]:


import networkx as nx

G = nx.read_graphml(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml")

print("Nodes:", G.number_of_nodes())
print("Edges:", G.number_of_edges())

# show one edge attributes (to see if geometry exists)
u, v, k = list(G.edges(keys=True))[0] if G.is_multigraph() else (*list(G.edges())[0], None)
print("Example edge:", u, v)
print("Edge data keys:", list(G.get_edge_data(u, v).keys()) if not G.is_multigraph() else list(G.get_edge_data(u, v, k).keys()))


# In[30]:


import geopandas as gpd

roads = gpd.read_file(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson")
print("Road features:", len(roads))
print(roads.geometry.type.value_counts().head())

roads.head(3)


# In[31]:


import json
import geopandas as gpd
import matplotlib.pyplot as plt

path = r"../GEOCODED/D202507130525.geojson"  # change file name

gdf = gpd.read_file(path)
print("CRS:", gdf.crs)
print("Geom types:\n", gdf.geometry.geom_type.value_counts())

ax = gdf.plot(figsize=(8,8))
plt.title(path.split("/")[-1])
plt.show()


# In[42]:


get_ipython().system('pip -q install folium ipywidgets')


# In[32]:


import geopandas as gpd
from pathlib import Path
import folium
import ipywidgets as widgets
from IPython.display import display, clear_output

geo_dir = Path("../GEOCODED")
files = sorted(geo_dir.glob("D*.geojson"))

def label_from_stem(stem: str) -> str:
    s = stem[1:13]  # YYYYMMDDHHMM
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"

out = widgets.Output()

def render_map(i):
    flood_path = files[i]
    flood = gpd.read_file(flood_path)

    # center map on flood bounds
    minx, miny, maxx, maxy = flood.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

    # add flood polygons
    folium.GeoJson(
        flood.__geo_interface__,
        name="Flood",
        style_function=lambda x: {
            "fillOpacity": 0.35,
            "weight": 1,
        },
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

def show(i):
    with out:
        clear_output(wait=True)
        print("Flood:", label_from_stem(files[i].stem), "|", files[i].name)
        display(render_map(i))

slider = widgets.IntSlider(value=0, min=0, max=len(files)-1, step=1, description="Flood t")
slider.observe(lambda ch: show(ch["new"]), names="value")

display(slider, out)
show(0)


# In[33]:


import geopandas as gpd

roads = gpd.read_file(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson").to_crs("EPSG:4326")

# make it lighter for web map rendering
roads = roads.sample(min(20000, len(roads)), random_state=1)   # optional: reduce
roads["geometry"] = roads.geometry.simplify(0.0001)            # simplify lines


# In[34]:


folium.GeoJson(
    roads.__geo_interface__,
    name="Roads",
    style_function=lambda x: {
        "color": "#333333",
        "weight": 1,
        "opacity": 0.35
    }
).add_to(m)


# In[35]:


import geopandas as gpd
from pathlib import Path
import folium
import ipywidgets as widgets
from IPython.display import display, clear_output

# --- load roads once (for visualization) ---
roads = gpd.read_file(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson").to_crs("EPSG:4326")
roads = roads.sample(min(20000, len(roads)), random_state=1)     # optional
roads["geometry"] = roads.geometry.simplify(0.0001)

# --- flood files ---
geo_dir = Path("../GEOCODED")
files = sorted(geo_dir.glob("D*.geojson"))

def label_from_stem(stem: str) -> str:
    s = stem[1:13]
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]} {s[8:10]}:{s[10:12]}"

out = widgets.Output()

def render_map(i):
    flood_path = files[i]
    flood = gpd.read_file(flood_path).to_crs("EPSG:4326")

    minx, miny, maxx, maxy = flood.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

    # Roads layer (toggleable)
    folium.GeoJson(
        roads.__geo_interface__,
        name="Roads",
        style_function=lambda x: {"weight": 1, "opacity": 0.35},
    ).add_to(m)

    # Flood layer (toggleable)
    folium.GeoJson(
        flood.__geo_interface__,
        name="Flood",
        style_function=lambda x: {"fillOpacity": 0.35, "weight": 1},
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

def show(i):
    with out:
        clear_output(wait=True)
        print("Flood:", label_from_stem(files[i].stem), "|", files[i].name)
        display(render_map(i))

slider = widgets.IntSlider(value=0, min=0, max=len(files)-1, step=1, description="Flood t")
slider.observe(lambda ch: show(ch["new"]), names="value")

display(slider, out)
show(0)


# In[36]:


from pathlib import Path
from datetime import datetime

geo_dir = Path("../GEOCODED")
all_files = sorted(geo_dir.glob("D*.geojson"))

def ts_from_filename(p: Path) -> datetime:
    # DYYYYMMDDHHMM*.geojson
    stem = p.stem  # e.g., D202507131155
    s = stem[1:13] # YYYYMMDDHHMM
    return datetime.strptime(s, "%Y%m%d%H%M")

start = datetime(2025, 7, 13, 11, 30)
end   = datetime(2025, 7, 13, 13, 30)

files = [p for p in all_files if start <= ts_from_filename(p) <= end]

print("Total flood files:", len(all_files))
print("Selected window files:", len(files))
print("First:", files[0].name, ts_from_filename(files[0]) if files else None)
print("Last :", files[-1].name, ts_from_filename(files[-1]) if files else None)


# In[37]:


import geopandas as gpd
import folium
import ipywidgets as widgets
from IPython.display import display, clear_output

def label(dt):
    return dt.strftime("%Y-%m-%d %H:%M")

out = widgets.Output()

def render_map(i):
    flood_path = files[i]
    flood = gpd.read_file(flood_path).to_crs("EPSG:4326")

    minx, miny, maxx, maxy = flood.total_bounds
    center_lat = (miny + maxy) / 2
    center_lon = (minx + maxx) / 2

    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles="OpenStreetMap")

    folium.GeoJson(
        flood.__geo_interface__,
        name="Flood",
        style_function=lambda x: {"fillOpacity": 0.35, "weight": 1},
    ).add_to(m)

    folium.LayerControl().add_to(m)
    return m

def show(i):
    with out:
        clear_output(wait=True)
        dt = ts_from_filename(files[i])
        print("Flood time:", label(dt), "|", files[i].name)
        display(render_map(i))

slider = widgets.IntSlider(value=0, min=0, max=len(files)-1, step=1, description="Flood t")
slider.observe(lambda ch: show(ch["new"]), names="value")

display(slider, out)
show(0)


# In[38]:


ORIGIN = (28.4726, 77.0726)  # IFFCO Chowk  (lat, lon)
DEST   = (28.4795, 77.0806)  # MG Road      (lat, lon)

import networkx as nx

# Try osmnx if available (best for nearest node)
try:
    import osmnx as ox
    OX = True
except Exception:
    OX = False

GRAPH_PATH = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml"  # adjust if needed

if OX:
    G = ox.load_graphml(GRAPH_PATH)
else:
    G = nx.read_graphml(GRAPH_PATH)

print("Loaded graph:", type(G), "nodes:", len(G.nodes), "edges:", len(G.edges))





# In[39]:


import geopandas as gpd
from shapely.ops import unary_union
from pathlib import Path

flood_path = Path("../GEOCODED/D202507131130.geojson")  # change to any timestamp you want
flood_gdf = gpd.read_file(flood_path).to_crs("EPSG:4326")
flood_union = unary_union(flood_gdf.geometry)

print("Flood polys:", len(flood_gdf))
print("Flood bounds:", flood_gdf.total_bounds)


# In[40]:


# check if graph edges already have geometry
count_geom = 0
for u, v, k, data in G.edges(keys=True, data=True):
    if "geometry" in data and data["geometry"] is not None:
        count_geom += 1

print("Edges with geometry:", count_geom, "out of", G.number_of_edges())


# In[41]:


import geopandas as gpd
roads = gpd.read_file(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson")
print(roads.columns)


# In[42]:


u, v, k, data = next(iter(G.edges(keys=True, data=True)))
print(data.keys())
count_osmid = sum(1 for _,_,_,d in G.edges(keys=True, data=True) if "osmid" in d and d["osmid"] is not None)
print("Edges with osmid:", count_osmid, "out of", G.number_of_edges())


# In[43]:


import geopandas as gpd

roads = gpd.read_file(r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson").to_crs("EPSG:4326")
roads2 = roads.explode(index_parts=False).copy()

osm_id_to_geom = dict(zip(roads2["osm_id"], roads2.geometry))
print("osm_id_to_geom size:", len(osm_id_to_geom))


# In[44]:


from shapely.geometry import LineString

def edge_geometry(u, v, data):
    # 1) graph geometry if present
    geom = data.get("geometry", None)
    if geom is not None:
        return geom

    # 2) lookup geometry via osmid -> osm_id
    osmid = data.get("osmid", None)
    if isinstance(osmid, (list, tuple, set)):
        for oid in osmid:
            if oid in osm_id_to_geom:
                return osm_id_to_geom[oid]
    else:
        if osmid in osm_id_to_geom:
            return osm_id_to_geom[osmid]

    # 3) fallback straight line
    ux, uy = float(G.nodes[u]["x"]), float(G.nodes[u]["y"])
    vx, vy = float(G.nodes[v]["x"]), float(G.nodes[v]["y"])
    return LineString([(ux, uy), (vx, vy)])


# In[45]:


# pick one edge and see if we can get geometry from mapping
u, v, k, data = next(iter(G.edges(keys=True, data=True)))
print("Example osmid:", data.get("osmid"))
geom = edge_geometry(u, v, data)
print("Geom type:", geom.geom_type)


# In[46]:


FLOOD_PENALTY_METERS = 1_000_000  # big so route avoids flooded edges

# Make sure lengths exist
for u, v, k, data in G.edges(keys=True, data=True):
    if "length" not in data:
        # if missing, approximate (not ideal)
        data["length"] = 1.0

# Apply penalty
flooded_count = 0
for u, v, k, data in G.edges(keys=True, data=True):
    geom = edge_geometry(u, v,data)
    is_flooded = geom.intersects(flood_union)
    data["is_flooded"] = bool(is_flooded)
    data["w_len"] = float(data["length"])
    data["w_flood"] = float(data["length"]) + (FLOOD_PENALTY_METERS if is_flooded else 0.0)
    if is_flooded:
        flooded_count += 1

print("Flooded edges:", flooded_count)


# In[47]:


orig_lat, orig_lon = ORIGIN
dest_lat, dest_lon = DEST

if OX:
    orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
    dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)
else:
    # simple fallback if osmnx not available
    # (slow on huge graphs; but works)
    def nearest_node(lat, lon):
        best, best_d = None, 1e18
        for n, nd in G.nodes(data=True):
            x, y = float(nd["x"]), float(nd["y"])
            d = (x - lon)**2 + (y - lat)**2
            if d < best_d:
                best_d = d
                best = n
        return best
    orig_node = nearest_node(orig_lat, orig_lon)
    dest_node = nearest_node(dest_lat, dest_lon)

print("Origin node:", orig_node, "Dest node:", dest_node)

# shortest (distance)
path_short = nx.shortest_path(G, orig_node, dest_node, weight="w_len")

# flood-aware
path_flood = nx.shortest_path(G, orig_node, dest_node, weight="w_flood")

print("Shortest nodes:", len(path_short), "| Flood-aware nodes:", len(path_flood))


# In[48]:


import folium

def path_to_latlon(path_nodes):
    coords = []
    for n in path_nodes:
        nd = G.nodes[n]
        coords.append((float(nd["y"]), float(nd["x"])))  # (lat, lon)
    return coords

m = folium.Map(location=[(ORIGIN[0]+DEST[0])/2, (ORIGIN[1]+DEST[1])/2], zoom_start=13)

# Flood overlay
folium.GeoJson(
    flood_gdf.__geo_interface__,
    name="Flood",
    style_function=lambda x: {"fillOpacity": 0.25, "weight": 1},
).add_to(m)

# Routes
folium.PolyLine(path_to_latlon(path_short), weight=5, opacity=0.9, tooltip="Shortest").add_to(m)
folium.PolyLine(path_to_latlon(path_flood), weight=5, opacity=0.9, tooltip="Flood-aware").add_to(m)

# Markers
folium.Marker([ORIGIN[0], ORIGIN[1]], tooltip="IFFCO Chowk").add_to(m)
folium.Marker([DEST[0], DEST[1]], tooltip="MG Road").add_to(m)

folium.LayerControl().add_to(m)
m


# In[49]:


from pathlib import Path
import geopandas as gpd
import networkx as nx
import folium
from shapely.ops import unary_union
from shapely.geometry import LineString

# Optional: osmnx for faster nearest node lookup
try:
    import osmnx as ox
    OX = True
except Exception:
    OX = False

# -------------------
# INPUTS (edit these)
# -------------------
ROADS_GEOJSON = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_roadways_clean.geojson"
GRAPH_PATH    = r"C:\Users\Varuni Singh\AIResqClimsol\Emulator for Traffic Forecasting\ggn_extent.graphml"
FLOOD_PATH    = Path("../GEOCODED/D202507131130.geojson")  # choose any flood snapshot

ORIGIN = (28.4726, 77.0726)  # IFFCO Chowk (lat, lon)
DEST   = (28.4795, 77.0806)  # MG Road (lat, lon)

FLOOD_PENALTY = 1_000_000  # large penalty so flooded edges are avoided


# In[50]:


# Purpose:
# Roads GeoJSON is NOT used for routing.
# It is used only to draw curved roads + to get true edge geometry by osm_id.
roads = gpd.read_file(ROADS_GEOJSON).to_crs("EPSG:4326")

# explode to ensure we only store LineStrings (not MultiLineStrings)
roads2 = roads.explode(index_parts=False).copy()

# Build mapping:
# osm_id (from roads geojson) -> LineString geometry
osm_id_to_geom = dict(zip(roads2["osm_id"], roads2.geometry))

print("Road segments loaded:", len(roads2))
print("osm_id_to_geom size:", len(osm_id_to_geom))


# In[51]:


# Purpose:
# Roads GeoJSON is NOT used for routing.
# It is used only to draw curved roads + to get true edge geometry by osm_id.
roads = gpd.read_file(ROADS_GEOJSON).to_crs("EPSG:4326")

# explode to ensure we only store LineStrings (not MultiLineStrings)
roads2 = roads.explode(index_parts=False).copy()

# Build mapping:
# osm_id (from roads geojson) -> LineString geometry
osm_id_to_geom = dict(zip(roads2["osm_id"], roads2.geometry))

print("Road segments loaded:", len(roads2))
print("osm_id_to_geom size:", len(osm_id_to_geom))


# In[52]:


# Purpose:
# flood_union = one big geometry for fast intersection tests
flood_gdf = gpd.read_file(FLOOD_PATH).to_crs("EPSG:4326")
flood_union = unary_union(flood_gdf.geometry)

print("Flood polygons:", len(flood_gdf))
print("Flood bounds:", flood_gdf.total_bounds)


# In[53]:


def edge_geometry(u, v, data):
    """
    Returns best available geometry for a graph edge.

    Priority:
    1) Graph edge 'geometry' (if already stored in GraphML)
    2) Use graph edge 'osmid' to lookup curve in roads geojson via osm_id_to_geom
    3) Fallback straight node-to-node line
    """
    # 1) graph geometry if present
    geom = data.get("geometry", None)
    if geom is not None:
        return geom

    # 2) osmid -> osm_id mapping (works for scalar or list)
    osmid = data.get("osmid", None)
    if isinstance(osmid, (list, tuple, set)):
        for oid in osmid:
            if oid in osm_id_to_geom:
                return osm_id_to_geom[oid]
    else:
        if osmid in osm_id_to_geom:
            return osm_id_to_geom[osmid]

    # 3) fallback straight line between nodes
    ux, uy = float(G.nodes[u]["x"]), float(G.nodes[u]["y"])
    vx, vy = float(G.nodes[v]["x"]), float(G.nodes[v]["y"])
    return LineString([(ux, uy), (vx, vy)])


# In[54]:


flooded_lines = []
flooded_count = 0

for u, v, k, data in G.edges(keys=True, data=True):
    geom = edge_geometry(u, v, data)
    is_flooded = geom.intersects(flood_union)

    # routing weights
    length = float(data.get("length", 1.0))
    data["w_len"] = length
    data["w_flood"] = length + (FLOOD_PENALTY if is_flooded else 0.0)
    data["is_flooded"] = bool(is_flooded)

    # for visualization (red flooded roads)
    if is_flooded:
        flooded_lines.append(geom)
        flooded_count += 1

flooded_edges_gdf = gpd.GeoDataFrame(geometry=flooded_lines, crs="EPSG:4326")
print("Flooded edges:", flooded_count)


# In[55]:


orig_lat, orig_lon = ORIGIN
dest_lat, dest_lon = DEST

if OX:
    orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
    dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)
else:
    # slower fallback
    def nearest_node(lat, lon):
        best, best_d = None, 1e18
        for n, nd in G.nodes(data=True):
            x, y = float(nd["x"]), float(nd["y"])
            d = (x - lon)**2 + (y - lat)**2
            if d < best_d:
                best_d = d
                best = n
        return best
    orig_node = nearest_node(orig_lat, orig_lon)
    dest_node = nearest_node(dest_lat, dest_lon)

# Routes:
path_short = nx.shortest_path(G, orig_node, dest_node, weight="w_len")
path_flood = nx.shortest_path(G, orig_node, dest_node, weight="w_flood")

print("Shortest nodes:", len(path_short), "| Flood-aware nodes:", len(path_flood))


# In[56]:


from shapely.ops import linemerge
from shapely.geometry import MultiLineString

def route_to_multiline(path_nodes):
    """
    Convert node-path to a MultiLineString using edge_geometry for each segment.
    """
    segs = []
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        # pick first edge key (good enough for now)
        k0 = next(iter(ed.keys()))
        data = ed[k0]
        segs.append(edge_geometry(a, b, data))
    return MultiLineString(segs)

short_geom = route_to_multiline(path_short)
flood_geom = route_to_multiline(path_flood)


# In[57]:


m = folium.Map(location=[(ORIGIN[0]+DEST[0])/2, (ORIGIN[1]+DEST[1])/2], zoom_start=14)

# Flood polygons (light blue)
folium.GeoJson(
    flood_gdf.__geo_interface__,
    name="Flood polygons",
    style_function=lambda x: {"fillColor":"#3399ff","color":"#3399ff","weight":1,"fillOpacity":0.20,"opacity":0.30},
).add_to(m)

# Flooded roads (red)
folium.GeoJson(
    flooded_edges_gdf.__geo_interface__,
    name="Flooded roads",
    style_function=lambda x: {"color":"red","weight":4,"opacity":0.9},
).add_to(m)

# Shortest route (blue) - now CURVED
folium.GeoJson(
    gpd.GeoSeries([short_geom], crs="EPSG:4326").__geo_interface__,
    name="Shortest route",
    style_function=lambda x: {"color":"blue","weight":6,"opacity":0.9},
).add_to(m)

# Flood-aware route (black) - now CURVED
folium.GeoJson(
    gpd.GeoSeries([flood_geom], crs="EPSG:4326").__geo_interface__,
    name="Flood-aware route",
    style_function=lambda x: {"color":"black","weight":6,"opacity":0.9},
).add_to(m)

# Markers
folium.Marker([ORIGIN[0], ORIGIN[1]], tooltip="IFFCO Chowk").add_to(m)
folium.Marker([DEST[0], DEST[1]], tooltip="MG Road").add_to(m)

folium.LayerControl().add_to(m)
m


# In[58]:


def route_distance_m(G, path_nodes):
    total = 0.0
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        # choose the edge key that minimizes the same weight used in routing
        # (for shortest route we used w_len which is length)
        best_k = min(ed, key=lambda k: float(ed[k].get("length", 1.0)))
        total += float(ed[best_k].get("length", 1.0))
    return total

d_short_km = route_distance_m(G, path_short) / 1000
d_flood_km = route_distance_m(G, path_flood) / 1000

print(f"Shortest distance:   {d_short_km:.2f} km")
print(f"Flood-aware distance:{d_flood_km:.2f} km")
print(f"Extra distance (detour): {(d_flood_km - d_short_km):.2f} km")

from shapely.ops import unary_union
flood_union = unary_union(flood_gdf.geometry)

def route_flood_stats(G, path_nodes):
    flooded = 0
    total = 0
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        k0 = next(iter(ed.keys()))
        geom = edge_geometry(a, b, ed[k0])
        total += 1
        if geom.intersects(flood_union):
            flooded += 1
    return flooded, total

f1, t1 = route_flood_stats(G, path_short)
f2, t2 = route_flood_stats(G, path_flood)

print(f"Shortest flooded edges: {f1}/{t1} ({(f1/t1*100 if t1 else 0):.1f}%)")
print(f"Flood-aware flooded edges: {f2}/{t2} ({(f2/t2*100 if t2 else 0):.1f}%)")


# In[59]:


legend_html = f"""
<div style="
 position: fixed; bottom: 30px; left: 30px; z-index: 9999;
 background: white; padding: 10px 12px; border:2px solid #444; border-radius:8px;
 font-size: 14px;">
 <b>Route Stats</b><br>
 <span style="color:blue;"><b>Shortest</b></span>: {d_short_km:.2f} km<br>
 <span style="color:black;"><b>Flood-aware</b></span>: {d_flood_km:.2f} km<br>
 Detour: {(d_flood_km - d_short_km):.2f} km
</div>
"""
m.get_root().html.add_child(folium.Element(legend_html))
m


# In[60]:


"""
Flood-aware routing demo with a TIME SLIDER (11:30 → 12:30).

What this does on every slider move:
1) Loads the selected flood snapshot GeoJSON.
2) Marks which road edges are flooded (geometry intersects flood polygons).
3) Computes 2 routes for the SAME OD:
   - Shortest (distance only)
   - Flood-aware (distance + big penalty on flooded edges)
4) Visualizes:
   - Flood polygons (light blue)
   - Flooded roads (red)
   - Shortest route (blue)
   - Flood-aware route (black)
   - Distance + flooded-edge counts in legend.

Performance optimization:
- Precompute edge geometries ONCE (edge_geom_cache) so slider updates are much faster.
- Use ONE loop per slider step to both set weights and collect flooded edges.
"""

from pathlib import Path
from datetime import datetime
import geopandas as gpd
import networkx as nx
import folium
import ipywidgets as widgets
from IPython.display import display, clear_output
from shapely.ops import unary_union
from shapely.geometry import MultiLineString


# =============================================================================
# Helpers (time parsing, route metrics, drawing geometries)
# =============================================================================

def ts_from_filename(p: Path) -> datetime:
    """Parse timestamp from filename like D202507131130.geojson → datetime(2025-07-13 11:30)."""
    s = p.stem[1:13]  # YYYYMMDDHHMM
    return datetime.strptime(s, "%Y%m%d%H%M")

def label_dt(dt: datetime) -> str:
    """Human readable datetime label."""
    return dt.strftime("%Y-%m-%d %H:%M")

def route_distance_m(G, path_nodes):
    """Sum of edge lengths (meters) along a node path."""
    total = 0.0
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        # choose the shortest-length edge among possible multiedges
        best_k = min(ed, key=lambda k: float(ed[k].get("length", 1.0)))
        total += float(ed[best_k].get("length", 1.0))
    return total

def route_flood_stats_from_cache(G, path_nodes, flood_union, edge_geom_cache):
    """Count how many edges in this route intersect the flood_union."""
    flooded = 0
    total = 0
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        # pick one representative edge key to test geometry
        k0 = next(iter(ed.keys()))
        geom = edge_geom_cache[(a, b, k0)]
        total += 1
        if geom.intersects(flood_union):
            flooded += 1
    return flooded, total

def route_to_multiline_from_cache(G, path_nodes, edge_geom_cache):
    """Convert node path to MultiLineString using cached edge geometries (curved rendering)."""
    segs = []
    for a, b in zip(path_nodes[:-1], path_nodes[1:]):
        ed = G.get_edge_data(a, b)
        if not ed:
            continue
        k0 = next(iter(ed.keys()))
        segs.append(edge_geom_cache[(a, b, k0)])
    return MultiLineString(segs)


# =============================================================================
# 1) Select flood files in a time window (11:30 → 12:30)
# =============================================================================

geo_dir = Path("../GEOCODED")
all_files = sorted(geo_dir.glob("D*.geojson"))

start = datetime(2025, 7, 13, 11, 30)
end   = datetime(2025, 7, 13, 12, 30)

files = [p for p in all_files if start <= ts_from_filename(p) <= end]

if not files:
    raise RuntimeError("No flood snapshots found in the selected time window. Check folder/path/time range.")

print("Selected flood snapshots:", len(files))
print("First:", files[0].name, "|", label_dt(ts_from_filename(files[0])))
print("Last :", files[-1].name, "|", label_dt(ts_from_filename(files[-1])))


# =============================================================================
# 2) Nearest nodes (compute once) — assumes ORIGIN, DEST, G already exist
# =============================================================================

orig_lat, orig_lon = ORIGIN
dest_lat, dest_lon = DEST

try:
    import osmnx as ox
    orig_node = ox.distance.nearest_nodes(G, orig_lon, orig_lat)
    dest_node = ox.distance.nearest_nodes(G, dest_lon, dest_lat)
except Exception:
    # fallback if osmnx isn't available
    def nearest_node(lat, lon):
        best, best_d = None, 1e18
        for n, nd in G.nodes(data=True):
            x, y = float(nd["x"]), float(nd["y"])
            d = (x - lon) ** 2 + (y - lat) ** 2
            if d < best_d:
                best_d = d
                best = n
        return best

    orig_node = nearest_node(orig_lat, orig_lon)
    dest_node = nearest_node(dest_lat, dest_lon)

print("Origin node:", orig_node, "Dest node:", dest_node)


# =============================================================================
# 3) PERFORMANCE: Cache edge geometries ONCE (roads do not change with time)
#    - Assumes edge_geometry(u,v,data) already exists from your earlier cells.
# =============================================================================

edge_geom_cache = {}
for u, v, k, data in G.edges(keys=True, data=True):
    edge_geom_cache[(u, v, k)] = edge_geometry(u, v, data)

print("Cached edge geometries:", len(edge_geom_cache))


# =============================================================================
# 4) UI + render logic
# =============================================================================

FLOOD_PENALTY = 1_000_000  # huge cost so route avoids flooded edges

out = widgets.Output()
slider = widgets.IntSlider(value=0, min=0, max=len(files) - 1, step=1, description="Flood t")


def render(i: int):
    flood_path = files[i]
    dt = ts_from_filename(flood_path)

    # A) Load flood snapshot
    flood_gdf = gpd.read_file(flood_path).to_crs("EPSG:4326")
    flood_union = unary_union(flood_gdf.geometry)

    # B) ONE PASS over edges:
    #    - decide flooded vs not
    #    - set weights w_len and w_flood
    #    - collect flooded edge geometries for red layer
    flooded_lines = []

    for u, v, k, data in G.edges(keys=True, data=True):
        geom = edge_geom_cache[(u, v, k)]
        is_flooded = geom.intersects(flood_union)

        length = float(data.get("length", 1.0))  # meters (graphml usually has this)
        data["w_len"] = length
        data["w_flood"] = length + (FLOOD_PENALTY if is_flooded else 0.0)

        if is_flooded:
            flooded_lines.append(geom)

    flooded_edges_gdf = gpd.GeoDataFrame(geometry=flooded_lines, crs="EPSG:4326")

    # C) Compute routes
    path_short = nx.shortest_path(G, orig_node, dest_node, weight="w_len")
    path_flood = nx.shortest_path(G, orig_node, dest_node, weight="w_flood")

    # D) Metrics
    d_short_km = route_distance_m(G, path_short) / 1000
    d_flood_km = route_distance_m(G, path_flood) / 1000

    f1, t1 = route_flood_stats_from_cache(G, path_short, flood_union, edge_geom_cache)
    f2, t2 = route_flood_stats_from_cache(G, path_flood, flood_union, edge_geom_cache)

    # E) Curved route geometries (draw nicely)
    short_geom = route_to_multiline_from_cache(G, path_short, edge_geom_cache)
    flood_geom = route_to_multiline_from_cache(G, path_flood, edge_geom_cache)

    # F) Build map
    m = folium.Map(
        location=[(ORIGIN[0] + DEST[0]) / 2, (ORIGIN[1] + DEST[1]) / 2],
        zoom_start=14,
        tiles="OpenStreetMap",
    )

    # Flood polygons (light blue)
    folium.GeoJson(
        flood_gdf.__geo_interface__,
        name="Flood polygons",
        style_function=lambda x: {
            "fillColor": "#3399ff",
            "color": "#3399ff",
            "weight": 1,
            "fillOpacity": 0.20,
            "opacity": 0.30,
        },
    ).add_to(m)

    # Flooded roads (red)
    folium.GeoJson(
        flooded_edges_gdf.__geo_interface__,
        name="Flooded roads",
        style_function=lambda x: {"color": "red", "weight": 3, "opacity": 0.9},
    ).add_to(m)

    # Shortest route (blue)
    folium.GeoJson(
        gpd.GeoSeries([short_geom], crs="EPSG:4326").__geo_interface__,
        name="Shortest (blue)",
        style_function=lambda x: {"color": "blue", "weight": 6, "opacity": 0.95},
    ).add_to(m)

    # Flood-aware route (black)
    folium.GeoJson(
        gpd.GeoSeries([flood_geom], crs="EPSG:4326").__geo_interface__,
        name="Flood-aware (black)",
        style_function=lambda x: {"color": "black", "weight": 6, "opacity": 0.95},
    ).add_to(m)

    # Markers
    folium.Marker([ORIGIN[0], ORIGIN[1]], tooltip="Origin").add_to(m)
    folium.Marker([DEST[0], DEST[1]], tooltip="Destination").add_to(m)
    folium.LayerControl().add_to(m)

    # Legend box
    legend_html = f"""
    <div style="position: fixed; bottom: 30px; left: 30px; z-index: 9999;
                background: white; padding: 10px 12px; border:2px solid #444; border-radius:8px;
                font-size: 14px;">
      <b>Flood time:</b> {label_dt(dt)}<br>
      <span style="color:blue;"><b>Shortest</b></span>: {d_short_km:.2f} km | flooded {f1}/{t1}<br>
      <span style="color:black;"><b>Flood-aware</b></span>: {d_flood_km:.2f} km | flooded {f2}/{t2}<br>
      <b>Detour:</b> {(d_flood_km - d_short_km):.2f} km
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Print + display
    print("Flood:", label_dt(dt), "|", flood_path.name)
    print(f"Shortest:    {d_short_km:.2f} km | flooded {f1}/{t1}")
    print(f"Flood-aware: {d_flood_km:.2f} km | flooded {f2}/{t2}")
    display(m)


def show(change=None):
    with out:
        clear_output(wait=True)
        render(slider.value)


slider.observe(show, names="value")
display(slider, out)
show()

