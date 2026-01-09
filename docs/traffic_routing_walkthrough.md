# Traffic-Aware Routing System - Complete Concept

## 🎯 Project Goal

Build a routing system that provides **intelligent route suggestions** in Gurugram by:
1. Finding the shortest path between two points
2. Considering **live traffic conditions** to avoid congestion
3. Avoiding **flooded roads** during monsoon/emergencies

---

## 📥 INPUTS

### Input 1: Road Network Graph (`ggn_extent.graphml`)

A graph representation of Gurugram's road network:

```
Nodes (44,077) = Road intersections
  └── Attributes: lat, lon (coordinates)

Edges (109,077) = Road segments connecting intersections
  └── Attributes:
      - length: distance in meters
      - name: road name (optional)
      - highway: road type (primary, secondary, residential)
      - maxspeed: speed limit (if available)
```

**Visual representation:**
```
    [Node A] ----edge (500m)---- [Node B]
       │                            │
       │                            │
    edge (200m)                 edge (300m)
       │                            │
       ▼                            ▼
    [Node C] ----edge (400m)---- [Node D]
```

---

### Input 2: Traffic Snapshot (`latest_traffic.json`)

Real-time traffic data from TomTom API:

```json
{
  "timestamp": "2026-01-07T00:45:00",
  "points": [
    {
      "name": "MG Road near Sector 14",
      "lat": 28.4574,
      "lon": 77.0266,
      "currentSpeed_kmph": 25,
      "freeFlowSpeed_kmph": 60,
      "speed_ratio": 0.42        // 42% of normal speed = HEAVY TRAFFIC
    },
    {
      "name": "Golf Course Road",
      "lat": 28.4512,
      "lon": 77.0945,
      "currentSpeed_kmph": 55,
      "freeFlowSpeed_kmph": 60,
      "speed_ratio": 0.92        // 92% of normal speed = SMOOTH
    }
    // ... 10 sample points total
  ]
}
```

**Key metric: `speed_ratio`**
| Speed Ratio | Meaning | Color |
|-------------|---------|-------|
| 0.85 - 1.0 | Free flowing | 🟢 Green |
| 0.65 - 0.85 | Moderate | 🟡 Yellow |
| 0.0 - 0.65 | Heavy congestion | 🔴 Red |

---

### Input 3: Flooded Roads (`flood_roads.geojson`)

GeoJSON with roads that are flooded/closed:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": { "name": "Sector 32 underpass", "status": "flooded" },
      "geometry": {
        "type": "LineString",
        "coordinates": [[77.02, 28.45], [77.03, 28.45]]
      }
    }
  ]
}
```

---

### Input 4: User Request

User clicks on map to set:
- **Origin**: (lat: 28.4525, lon: 77.0181)  → "Near Sector 15"
- **Destination**: (lat: 28.4658, lon: 77.0723) → "Sector 31"

---

## 🔄 PROCESSING LOGIC

### Step 1: Load & Prepare Graph

```python
# Load road network
graph = load_graphml("ggn_extent.graphml")
# 44,077 nodes, 109,077 edges
```

### Step 2: Add Traffic Costs to Edges

For each edge in the graph, calculate a "traffic cost":

```python
# Without traffic awareness:
edge_cost = length  # Just distance

# With traffic awareness:
edge_cost = length / speed_ratio
# Slow roads get HIGHER cost → algorithm avoids them
```

**Example:**
| Road | Length | Speed Ratio | Traffic Cost |
|------|--------|-------------|--------------|
| MG Road | 500m | 0.42 (slow) | 500/0.42 = **1190** |
| Golf Course Rd | 500m | 0.92 (fast) | 500/0.92 = **543** |

The algorithm will prefer Golf Course Road (lower cost) even if same length!

### Step 3: Mark Flooded Roads

```python
for edge in graph.edges:
    if edge intersects with flooded_roads:
        edge['flood_cost'] = 999999  # Effectively blocked
```

### Step 4: Find Routes

```python
# Route 1: SHORTEST (ignores traffic & floods)
shortest = dijkstra(graph, origin, dest, weight="length")

# Route 2: TRAFFIC-AWARE (avoids congestion)
traffic_aware = dijkstra(graph, origin, dest, weight="traffic_cost")

# Route 3: SUGGESTED (avoids congestion AND floods)
suggested = dijkstra(graph, origin, dest, weight="combined_cost")
# where combined_cost = traffic_cost + flood_cost
```

---

## 📤 EXPECTED OUTPUTS

### Output 1: Three Different Routes on Map

```
SCENARIO: There's heavy traffic on the direct route via MG Road,
          and Sector 32 underpass is flooded.

┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    🟢 Origin                                                │
│      │                                                      │
│      │──── BLUE (Shortest): Via MG Road                     │
│      │     Distance: 4.2 km, ETA: 25 min                   │
│      │     ⚠️ Goes through traffic!                         │
│      │                                                      │
│      │──── RED (Traffic-aware): Via Golf Course Road        │
│      │     Distance: 5.1 km, ETA: 12 min                   │
│      │     ✅ Avoids congestion                             │
│      │                                                      │
│      │──── GREEN (Suggested): Via Sohna Road               │
│      │     Distance: 5.8 km, ETA: 14 min                   │
│      │     ✅ Avoids congestion AND floods                  │
│      ▼                                                      │
│    🔴 Destination                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Output 2: Route Details (Popup on Click)

```json
{
  "route_type": "traffic_aware",
  "distance_m": 5100,
  "eta_seconds": 720,
  "eta_formatted": "12 min",
  "avoided": ["MG Road congestion"],
  "geometry": [[77.018, 28.452], [77.025, 28.458], ...]
}
```

### Output 3: Visual Comparison

| Route | Distance | ETA | Why? |
|-------|----------|-----|------|
| 🔵 Shortest | 4.2 km | 25 min | Stuck in traffic |
| 🔴 Traffic-aware | 5.1 km | **12 min** | Longer but faster |
| 🟢 Suggested | 5.8 km | 14 min | Safest, avoids flood |

---

## 🧪 How to Verify It Works

### Test Case 1: Traffic Impact
1. Set origin/destination through a known congested area
2. **Shortest route** should go through it
3. **Traffic-aware route** should go around it
4. If they're the same → traffic data not being used

### Test Case 2: Flood Impact
1. Set route that would normally pass through flooded road
2. **Suggested route** should avoid the flooded area
3. **Shortest route** may still show it (with warning?)

---

## 📊 Summary Diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         INPUTS                                    │
├──────────────────┬──────────────────┬───────────────────────────┤
│   Road Network   │  Traffic Data    │   Flood Data              │
│   (GraphML)      │  (JSON)          │   (GeoJSON)               │
│   44K nodes      │  10 points       │   Flooded roads           │
│   109K edges     │  speed_ratio     │   Closed roads            │
└────────┬─────────┴────────┬─────────┴─────────────┬─────────────┘
         │                  │                       │
         ▼                  ▼                       ▼
┌──────────────────────────────────────────────────────────────────┐
│                      PROCESSING                                   │
│  1. Map traffic points → nearby edges                            │
│  2. Calculate traffic_cost = length / speed_ratio                │
│  3. Mark flooded roads with high penalty                         │
│  4. Run Dijkstra with different weights                          │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                         OUTPUTS                                   │
├──────────────────┬──────────────────┬───────────────────────────┤
│  🔵 Shortest     │  🔴 Traffic      │  🟢 Suggested              │
│  Pure distance   │  Avoids jams     │  Avoids jams + floods     │
│  May be slow     │  Often fastest   │  Safest option            │
└──────────────────┴──────────────────┴───────────────────────────┘
```

---

## ❓ Questions to Consider

1. **How to map 10 traffic points to 109K edges?**
   - Use spatial proximity (nearest edges) + interpolation

2. **What if no traffic data for an area?**
   - Use default speed_ratio = 1.0 (assume free flow)

3. **How often to refresh traffic costs?**
   - Every 2-5 minutes for real-time accuracy

---

Ready to implement? Let me know! 🚀
