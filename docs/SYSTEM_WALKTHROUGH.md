# 🚗 Gurugram Smart Traffic & Flood Routing System
## Complete Technical Walkthrough

---

## 🎯 What Does This System Do?

Imagine you're driving in Gurugram during monsoon season. Roads are flooded, traffic is heavy. **This system helps you find the best route** by:

1. **Avoiding deep floods** (water depth > 30cm)
2. **Using shallow floods** (water depth ≤ 30cm) when safe
3. **Avoiding traffic congestion**
4. **Showing you WHY a particular route is recommended**

---

## 🗺️ The Data Files We Use

### 1. Road Network (`ggn_extent.graphml`)
```
What it is: A map of ALL roads in Gurugram
Format: GraphML (a graph database format)
Contains: ~50,000+ road segments (edges) and intersections (nodes)

Each road segment has:
├── length (in meters)
├── maxspeed (speed limit)
├── geometry (actual road shape)
└── road type (highway, residential, etc.)
```

### 2. Flood Data (`GEOCODED/D*.geojson`)
```
What it is: Flood prediction at different times
Format: GeoJSON (geographic polygons)
Contains: 337 time snapshots

Each flood polygon has:
├── geometry (area covered by water)
└── depth (water depth in meters)
```

### 3. Traffic Data (`latest_traffic.json`)
```
What it is: Real-time traffic speed data
Format: JSON with lat/lon points
Contains: ~10 traffic monitoring points

Each point has:
├── latitude, longitude
├── speed_ratio (0.1 to 1.0)
│   └── 1.0 = free flow, 0.1 = almost stopped
└── current speed
```

---

## 🧠 The Core Concept: Weighted Graph

### What is a Graph?

Think of roads as a **network**:

```
    [A] ----500m---- [B] ----300m---- [C]
     |                |                |
   200m             400m             600m
     |                |                |
    [D] ----350m---- [E] ----450m---- [F]
```

- **Nodes** = Intersections (A, B, C, D, E, F)
- **Edges** = Roads connecting them (with distance/weight)

### How Do We Find "Best" Route?

We use **Dijkstra's Algorithm** - like a GPS calculating the shortest path.

**Simple example:**
```
From A to C, two options:

Option 1: A → B → C
Distance: 500m + 300m = 800m ✅ Shorter!

Option 2: A → D → E → B → C  
Distance: 200m + 350m + 400m + 300m = 1250m
```

Dijkstra automatically finds the **lowest total weight** path.

---

## 📊 Four Types of Routes

### 1. Shortest (Distance)
```
Weight = Road Length in meters

Example:
Road A-B: 500m → weight = 500
Road B-C: 300m → weight = 300

Total weight = 800 → Algorithm picks this if lowest
```

### 2. Fastest (Traffic-Aware)
```
Weight = Travel Time in seconds

Formula: travel_time = length ÷ current_speed

Example (no traffic):
Road 1km, speed 30 km/h
travel_time = 1000m ÷ (30 × 1000/3600) = 120 seconds

Example (heavy traffic):
Road 1km, speed reduced to 10 km/h (speed_ratio = 0.33)
travel_time = 1000m ÷ (10 × 1000/3600) = 360 seconds

Algorithm avoids road with 360s, picks road with 120s
```

### 3. Flood-Avoiding
```
Weight = Length + Flood Penalty

Flood Penalty Logic:
├── Depth > 0.3m → Add 1,000,000 meters (HUGE penalty!)
├── Depth ≤ 0.3m → No penalty (safe to cross)
└── No flood → No penalty

Example:
Road A: 500m, no flood → weight = 500
Road B: 300m, depth 0.5m → weight = 300 + 1,000,000 = 1,000,300
Road C: 400m, depth 0.2m → weight = 400 (safe!)

Algorithm picks: A → C (ignores B completely)
```

### 4. Smart (Avoids Both)
```
Weight = Travel Time + Flood Penalty

Combines traffic slowness AND flood danger
```

---

## 🌊 How Flood Detection Works

### Step 1: Load Flood Polygons
```
From file: GEOCODED/D202507131330.geojson
(Date: 2025-07-13, Time: 13:30)

Contains polygons like:
{
  "geometry": { "type": "Polygon", "coordinates": [...] },
  "properties": { "depth": 0.45 }  ← 45cm water
}
```

### Step 2: Find Roads Inside Flood Areas
```
Method: Spatial Join (sjoin)

Road Network           Flood Polygons
     │                      │
     └──────► OVERLAP ◄─────┘
                 │
                 ▼
        "These 150 roads are flooded"
```

### Step 3: Filter by Depth
```
All flooded roads (150)
        │
        ▼
   Depth > 0.3m?
   ├── YES → Mark as DANGEROUS (add penalty)
   └── NO  → Mark as PASSABLE (no penalty)
```

### Visual Result
```
┌─────────────────────────────────────┐
│  Blue solid line = All flooded roads│
│  Green dashed   = Route uses this   │
│                   (shallow, safe)   │
└─────────────────────────────────────┘
```

---

## 🔢 The Math: Dijkstra's Algorithm

### Simplified Explanation

Imagine finding shortest path from A to Z in a maze:

```
Start at A:
├── Look at all neighbors
├── Calculate distance to each
├── Pick the closest one
├── Move there
└── Repeat until reach Z
```

### Actual Example

```
Graph:
    [Start] --100m-- [X] --50m-- [End]
       │              │
      200m          150m
       │              │
       └─── [Y] ──────┘

From Start to End:

Path 1: Start → X → End = 100 + 50 = 150m ✅ Winner!
Path 2: Start → Y → End = 200 + 150 = 350m
Path 3: Start → X → Y → End = 100 + 150 = 250m
```

The algorithm efficiently finds Path 1 without checking everything.

---

## 🚦 Traffic Speed Application

### How Traffic Data Affects Routes

```
Normal Road:
├── Length: 1000m
├── Free-flow speed: 40 km/h
├── Travel time: 90 seconds

Congested Road (speed_ratio = 0.5):
├── Length: 1000m  
├── Actual speed: 40 × 0.5 = 20 km/h
├── Travel time: 180 seconds (DOUBLE!)

Algorithm picks the 90-second road
```

### Finding Affected Roads
```
Traffic Point: (lat: 28.47, lon: 77.07, speed_ratio: 0.3)
        │
        ▼
   Find nearest road edge (using spatial index)
        │
        ▼
   Update that edge's travel_time
```

---

## 🎨 Visual Features Explained

### 1. Route Colors
```
Purple = Shortest (distance only)
Brown  = Fastest (avoids traffic)
Green  = Flood-avoiding
Black  = Smart (avoids both)
```

### 2. Flooded Roads Layer
```
Blue solid = All roads with water
(Click to see details)
```

### 3. Green Dashed Overlay
```
Appears ON the route when:
├── Route type is flood_avoid or smart
├── Route crosses roads with water
└── Water depth ≤ 0.3m (safe)

ONLY shown on the specific flooded segments
```

### 4. Route Popup Information
```
┌─────────────────────────────────┐
│ FLOOD AVOID                      │
│ Distance: 3.2 km                 │
│ ETA: 8.5 min                     │
│ Avg Speed: 22.6 km/h             │
│ 🌊 Uses 0.5 km shallow flood    │
└─────────────────────────────────┘
```

---

## 📱 How the System Works (End-to-End)

### User Journey

```
1. User opens http://localhost:8000
        │
2. Map loads with Gurugram roads
        │
3. User selects flood time (slider)
        │
4. Flooded roads appear in blue
        │
5. User picks origin & destination
        │
6. Clicks "Calculate Route"
        │
7. Backend processes:
   ├── Loads road graph
   ├── Applies traffic data
   ├── Applies flood penalties
   └── Runs Dijkstra algorithm
        │
8. Results shown:
   ├── Routes on map
   ├── Green overlay on shallow floods
   └── Popup with details
```

---

## 🔧 Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Backend | Python + Flask | API server |
| Routing | NetworkX | Graph algorithms |
| Spatial | GeoPandas + Shapely | Geographic operations |
| Frontend | HTML + JavaScript | User interface |
| Maps | Leaflet.js | Interactive maps |
| Basemap | Google Maps tiles | Background map |

---

## 📁 File Structure

```
gurugram_traffic_prevention/
├── server/
│   ├── api.py          ← HTTP API endpoints
│   └── routing.py      ← Route calculation logic
│
├── web/
│   ├── index.html      ← Dashboard UI
│   ├── app.js          ← Map & route logic
│   ├── style.css       ← Styling
│   │
│   └── data/
│       ├── ggn_extent.graphml    ← Road network
│       ├── clean_roads.geojson   ← Road visualization
│       ├── latest_traffic.json   ← Traffic data
│       └── GEOCODED/
│           └── D*.geojson        ← 337 flood snapshots
```

---

## 🎓 Key Concepts Summary

| Concept | Simple Explanation |
|---------|-------------------|
| **Graph** | Roads as connected network |
| **Dijkstra** | Find lowest-cost path |
| **Weight** | "Cost" of using a road |
| **Spatial Join** | Find roads inside flood areas |
| **Penalty** | Huge number to discourage usage |
| **Depth Threshold** | 0.3m = max safe water level |

---

## 🚀 Example Scenario

**Situation:** Monsoon flooding in Gurugram, user needs to go from IFFCO Chowk to Cyber Hub.

**Three routes available:**

| Route | Distance | Via | Issue |
|-------|----------|-----|-------|
| Direct | 5 km | NH-48 | 0.5m flood 🚫 |
| Alternate | 7 km | MG Road | 0.2m flood ✅ |
| Long | 10 km | Outer Ring | No flood |

**What our system does:**

1. ❌ Avoids NH-48 (deep flood - adds 1,000,000m penalty)
2. ✅ Picks MG Road (shallow flood - no penalty)
3. Shows green dashed overlay on MG Road flooded section
4. Popup shows: "Uses 0.8 km shallow flood (≤0.3m)"

**User understands:** "This route goes through some water, but it's shallow and safe!"

---

## 📊 Performance Optimizations Made

| Problem | Solution | Improvement |
|---------|----------|------------|
| Slow shortest path | Skip traffic data for distance-only routes | ~3x faster |
| Slow traffic routes | One-time travel_time initialization | First request cached |
| Slow flood detection | Cache flood edge sets | Subsequent requests instant |

---

*This system helps people navigate safely during floods by intelligently routing around dangerous water while allowing passage through shallow, safe areas.*
