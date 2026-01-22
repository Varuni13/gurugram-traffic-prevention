# 🚗 Gurugram Mobility Dashboard

<div align="center">

![Traffic Monitoring](https://img.shields.io/badge/Traffic-Monitoring-blue)
![Flood Aware](https://img.shields.io/badge/Flood-Aware-green)
![Real Time](https://img.shields.io/badge/Real-Time-orange)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-2.0+-black?logo=flask)
![Leaflet](https://img.shields.io/badge/Leaflet-1.9+-green?logo=leaflet)

**A real-time traffic and flood monitoring system for Gurugram (Gurgaon), India**

[Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [API Reference](#-api-reference) • [Configuration](#-configuration)

</div>

---

## 📖 Overview

The **Gurugram Mobility Dashboard** is a comprehensive web-based application designed to help commuters navigate Gurugram's roads during normal conditions and extreme weather events like floods. The system integrates real-time traffic data from the TomTom API with historical flood information to provide intelligent routing recommendations.

### What Problem Does It Solve?

Gurugram faces significant challenges during monsoon season:
- **Urban Flooding**: Low-lying areas become waterlogged, making roads impassable
- **Traffic Congestion**: Major intersections experience severe bottlenecks during peak hours
- **Route Planning**: Drivers struggle to find safe, efficient routes during adverse conditions

This dashboard addresses these challenges by:
1. Providing **real-time traffic visualization** at 25 major hotspots
2. Offering **flood-aware routing** that avoids waterlogged roads
3. Enabling **time-travel simulation** to analyze historical flood scenarios
4. Supporting **multiple routing strategies** (shortest, fastest, flood-avoiding, smart)

---

## ✨ Features

### 🚦 Live Traffic Dashboard
- **Real-time Traffic Status Cards**: Visual indicators showing traffic conditions (Smooth/Moderate/Heavy) at each monitored location
- **Traffic Trend Chart**: Interactive Chart.js visualization showing historical traffic patterns over time
- **Auto-Refresh**: Automatic data updates with toast notifications when traffic conditions change significantly
- **Traffic Metrics**: Current speed, free flow speed, and congestion ratios for each location

### 🗺️ Interactive Map
- **Leaflet-based Map**: Smooth, responsive map interface with zoom and pan controls
- **Traffic Overlay**: Color-coded road segments showing real-time traffic density
- **TomTom Traffic Tiles**: High-quality traffic flow visualization layer
- **Marker Clustering**: Efficient display of multiple traffic points
- **Click-to-Route**: Click on the map to set origin/destination points

### 🌊 Flood Data Visualization
- **Time Slider Control**: Navigate through flood timeline to see conditions at different times
- **Flooded Road Overlay**: Visual representation of road segments affected by flooding
- **Flood Polygon Display**: GeoJSON-based flood area boundaries
- **Dynamic Intersection**: Real-time calculation of roads intersecting with flood zones

### 🛣️ Smart Routing Engine
- **Multiple Route Types**:
  - `shortest`: Minimum distance path
  - `fastest`: Minimum travel time (traffic-aware)
  - `flood_avoid`: Routes that completely avoid flooded roads
  - `smart`: Balanced approach considering all factors
- **Real-time Traffic Integration**: Route calculations factor in current traffic conditions
- **Progressive Caching**: Frequently used routes are cached for instant retrieval
- **Turn-by-Turn Directions**: Detailed navigation instructions

### 🌙 User Experience
- **Dark Mode Support**: Toggle between light and dark themes for comfortable viewing
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Toast Notifications**: Non-intrusive alerts for traffic changes and system events
- **Loading States**: Visual feedback during data fetching and route calculation

### 📊 Traffic Data Collection
- **Automated Collection**: Background scheduler fetches traffic data at configurable intervals
- **Smart Scheduling**: More frequent collection during peak hours, reduced during off-peak
- **API Optimization**: Designed to stay within TomTom's free tier (2,500 calls/day)
- **Historical Storage**: All traffic snapshots are saved for trend analysis

---

## 🛠️ Technology Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **Python** | 3.8+ | Primary programming language |
| **Flask** | 2.0+ | Lightweight web framework for REST API |
| **Flask-CORS** | 3.0+ | Cross-Origin Resource Sharing support |
| **Waitress** | 2.0+ | Production-ready WSGI server |
| **NetworkX** | 2.6+ | Graph-based routing algorithms (Dijkstra, A*) |
| **OSMnx** | 1.0+ | OpenStreetMap network analysis (optional) |
| **GeoPandas** | 0.10+ | Geospatial data processing and analysis |
| **Shapely** | 1.8+ | Geometric operations (intersection, buffering) |
| **Requests** | 2.25+ | HTTP client for TomTom API calls |
| **python-dotenv** | 0.19+ | Environment variable management |
| **APScheduler** | 3.8+ | Background job scheduling |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **HTML5** | - | Semantic markup and structure |
| **CSS3** | - | Styling with CSS Grid and Flexbox |
| **JavaScript** | ES6+ | Application logic and interactivity |
| **Leaflet.js** | 1.9+ | Interactive map rendering |
| **Chart.js** | 3.0+ | Traffic trend visualizations |
| **TomTom SDK** | - | Geocoding and traffic tile services |

### Data Formats

| Format | Extension | Usage |
|--------|-----------|-------|
| **GeoJSON** | `.geojson` | Roads, flood polygons, route geometries |
| **GraphML** | `.graphml` | Road network graph for routing |
| **JSON** | `.json` | Traffic snapshots, configuration, cache |
| **CSV** | `.csv` | Historical traffic data export |

### External APIs

| API | Provider | Purpose |
|-----|----------|---------|
| **Traffic Flow** | TomTom | Real-time traffic speed and congestion data |
| **Traffic Tiles** | TomTom | Visual traffic layer for map |
| **Geocoding** | TomTom | Address to coordinates conversion |
| **Map Tiles** | OpenStreetMap | Base map imagery |

---

## 📦 Installation

### Prerequisites

Before installing, ensure you have:

- **Python 3.8 or higher** - [Download Python](https://www.python.org/downloads/)
- **pip** - Python package manager (included with Python)
- **Git** - For cloning the repository
- **TomTom API Key** - [Get free key](https://developer.tomtom.com) (2,500 free calls/day)

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/gurugram-traffic-prevention.git
cd gurugram-traffic-prevention
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Core dependencies (required)
pip install flask flask-cors waitress requests python-dotenv

# Geospatial libraries (required for flood-road intersection)
pip install geopandas shapely pyproj

# Routing dependencies (required for smart routing)
pip install networkx

# Optional: Advanced network analysis
pip install osmnx

# Optional: Background scheduling
pip install apscheduler
```

Or install all at once:

```bash
pip install flask flask-cors waitress requests python-dotenv geopandas shapely pyproj networkx apscheduler
```

### Step 4: Configure Environment Variables

Create a `.env` file in the project root directory:

```bash
# Copy the example configuration
cp .env.example .env

# Or create manually
touch .env
```

Add the following configuration to your `.env` file:

```env
# ===========================================
# SERVER CONFIGURATION
# ===========================================
FLASK_HOST=0.0.0.0
FLASK_PORT=8000
FLASK_DEBUG=False

# ===========================================
# CORS CONFIGURATION
# ===========================================
CORS_ENABLED=True
CORS_ORIGINS=*

# ===========================================
# API KEYS (REQUIRED)
# ===========================================
# Get your free API key from: https://developer.tomtom.com
TOMTOM_API_KEY=your_tomtom_api_key_here

# ===========================================
# ROUTING CONFIGURATION
# ===========================================
# Minimum flood depth (in meters) to consider a road blocked
FLOOD_DEPTH_THRESHOLD_M=0.3

# Maximum number of routes to cache
MAX_ROUTE_CACHE_SIZE=500

# Penalty weight applied to flooded road edges
FLOOD_PENALTY=1000000.0

# Radius (in meters) for traffic data influence
TRAFFIC_BUFFER_M=500

# ===========================================
# TRAFFIC COLLECTOR SETTINGS
# ===========================================
# Collection interval in minutes
COLLECTOR_INTERVAL_MIN=10

# Peak hours definition (24-hour format)
PEAK_START_HOUR=6
PEAK_END_HOUR=21

# Off-peak collection interval in minutes
OFFPEAK_INTERVAL_MIN=60

# ===========================================
# FRONTEND TIME FILTER
# ===========================================
# Default time range for flood timeline
TIMES_START=2025-07-13T11:25
TIMES_END=2025-07-13T18:17
```

### Step 5: Verify Installation

Run the configuration checker:

```bash
python config.py
```

You should see output similar to:

```
========================================
 Configuration Summary
========================================
Server: 0.0.0.0:8000
Debug: False
CORS: Enabled (origins: *)
TomTom API: Configured ✓

Paths:
  - Web: C:\...\web
  - Data: C:\...\web\data
  - Graph: C:\...\ggn_extent.graphml ✓

Routing:
  - Flood threshold: 0.3m
  - Cache size: 500
  - Flood penalty: 1000000.0
========================================
```

---

## 🚀 Quick Start

### Running the Application

#### Option 1: Combined Server + Scheduler (Recommended)

This starts both the API server and the traffic data collector:

```bash
python server.py
```

Output:
```
[INFO] Starting Gurugram Mobility Dashboard...
[INFO] Traffic collector scheduler started
[INFO] Server running on http://0.0.0.0:8000
```

#### Option 2: Server Only

If you only need the API server without automatic traffic collection:

```bash
# Production mode with Waitress
python -c "from server.api import app; from waitress import serve; serve(app, host='0.0.0.0', port=8000)"

# Development mode with Flask's built-in server
set FLASK_DEBUG=True
python -m flask run --host=0.0.0.0 --port=8000
```

#### Option 3: Run Components Separately

**Traffic Collector Only:**

```bash
# One-time collection
python collector/collect_tomtom.py

# Continuous collection with smart scheduling
python collector/run_scheduler.py

# Run as background daemon
python collector/run_scheduler.py --daemon

# Check scheduler status
python collector/run_scheduler.py --status

# Stop the scheduler
python collector/run_scheduler.py --stop
```

### Accessing the Dashboard

1. Open your web browser
2. Navigate to: **http://localhost:8000**
3. The dashboard will load with the interactive map and traffic data

### First-Time Setup Checklist

- [ ] TomTom API key configured in `.env`
- [ ] All Python dependencies installed
- [ ] `ggn_extent.graphml` exists in `web/data/`
- [ ] `clean_roads.geojson` exists in `web/data/`
- [ ] Flood data files exist in `web/data/GEOCODED/`

---

## 📡 API Reference

### Base URL

```
http://localhost:8000/api
```

### Flood Data Endpoints

#### Get Flood Times

Returns a list of available flood time periods.

```http
GET /api/flood
```

**Response:**
```json
{
  "times": [
    "2025-07-13T11:25",
    "2025-07-13T11:30",
    "2025-07-13T11:35"
  ],
  "count": 42
}
```

---

#### Get Flood Times (Filtered)

Filter flood times by date range.

```http
GET /api/flood?start={start_time}&end={end_time}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `start` | string | Start time (ISO format) |
| `end` | string | End time (ISO format) |

**Example:**
```bash
curl "http://localhost:8000/api/flood?start=2025-07-13T12:00&end=2025-07-13T14:00"
```

---

#### Get Flood Polygons

Returns GeoJSON of flood polygon areas for a specific time.

```http
GET /api/flood/polygons?time={time_index}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `time` | integer | Index of the time period (0-based) |

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[77.0, 28.4], [77.1, 28.4], ...]]
      },
      "properties": {
        "depth": 0.5,
        "area_sqm": 1234.56
      }
    }
  ]
}
```

---

#### Get Flooded Roads

Returns GeoJSON of road segments intersecting with flood zones.

```http
GET /api/flood/roads?time={time_index}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `time` | integer | Index of the time period (0-based) |

**Response:**
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [[77.0, 28.4], [77.01, 28.41]]
      },
      "properties": {
        "road_name": "Golf Course Road",
        "flood_depth": 0.4
      }
    }
  ]
}
```

---

### Traffic Data Endpoints

#### Get Latest Traffic

Returns the most recent traffic snapshot.

```http
GET /api/traffic
```

**Response:**
```json
{
  "timestamp": "2025-07-13T14:30:00Z",
  "points": [
    {
      "id": 1,
      "name": "IFFCO Chowk",
      "lat": 28.4725,
      "lon": 77.0722,
      "current_speed": 25,
      "free_flow_speed": 60,
      "congestion_ratio": 0.42,
      "status": "moderate"
    }
  ]
}
```

---

#### Get Traffic (Synced to Flood Time)

Returns traffic data aligned with the flood timeline.

```http
GET /api/traffic/sync?time={time_index}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `time` | integer | Index of the flood time period |

---

#### Get Traffic Metadata

Returns information about available traffic data.

```http
GET /api/traffic/meta
```

**Response:**
```json
{
  "total_snapshots": 156,
  "latest_timestamp": "2025-07-13T14:30:00Z",
  "oldest_timestamp": "2025-07-10T06:00:00Z",
  "collection_interval": "10 minutes"
}
```

---

#### Refresh Traffic Data

Triggers an immediate traffic data collection.

```http
POST /api/traffic/refresh
```

**Response:**
```json
{
  "status": "success",
  "message": "Traffic data refreshed",
  "timestamp": "2025-07-13T14:35:00Z"
}
```

---

### Routing Endpoints

#### Calculate Route

Calculates an optimal route between two points.

```http
GET /api/route?origin_lat={lat}&origin_lon={lon}&dest_lat={lat}&dest_lon={lon}&type={route_type}&flood_time={time}
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `origin_lat` | float | Yes | Starting latitude |
| `origin_lon` | float | Yes | Starting longitude |
| `dest_lat` | float | Yes | Destination latitude |
| `dest_lon` | float | Yes | Destination longitude |
| `type` | string | No | Route type: `shortest`, `fastest`, `flood_avoid`, `smart` (default: `fastest`) |
| `flood_time` | integer | No | Flood time index for flood-aware routing |

**Example:**
```bash
curl "http://localhost:8000/api/route?origin_lat=28.4595&origin_lon=77.0266&dest_lat=28.4725&dest_lon=77.0722&type=flood_avoid&flood_time=5"
```

**Response:**
```json
{
  "route": {
    "type": "Feature",
    "geometry": {
      "type": "LineString",
      "coordinates": [[77.0266, 28.4595], [77.0300, 28.4600], ...]
    },
    "properties": {
      "distance_km": 5.2,
      "duration_min": 18,
      "route_type": "flood_avoid"
    }
  },
  "instructions": [
    {"step": 1, "instruction": "Head east on NH-48", "distance": "1.2 km"},
    {"step": 2, "instruction": "Turn right onto Golf Course Road", "distance": "2.5 km"}
  ],
  "alternatives": []
}
```

---

#### Get Graph Statistics

Returns information about the road network graph.

```http
GET /api/route/graph-stats
```

**Response:**
```json
{
  "nodes": 15234,
  "edges": 23456,
  "connected_components": 1,
  "average_degree": 3.08,
  "graph_loaded": true
}
```

---

#### Get Cache Statistics

Returns route cache performance metrics.

```http
GET /api/route/cache-stats
```

**Response:**
```json
{
  "cache_size": 127,
  "max_size": 500,
  "hit_rate": 0.73,
  "total_requests": 1543,
  "cache_hits": 1126
}
```

---

### TomTom Proxy Endpoints

#### Geocode Location

Searches for a location and returns coordinates.

```http
GET /api/tomtom/geocode?query={search_query}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | string | Location search query |

**Example:**
```bash
curl "http://localhost:8000/api/tomtom/geocode?query=IFFCO%20Chowk%20Gurugram"
```

**Response:**
```json
{
  "results": [
    {
      "address": "IFFCO Chowk, Sector 29, Gurugram, Haryana",
      "position": {
        "lat": 28.4725,
        "lon": 77.0722
      }
    }
  ]
}
```

---

#### Get Traffic Tiles

Returns traffic visualization tiles for the map.

```http
GET /api/tomtom/traffic/{z}/{x}/{y}.png
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `z` | integer | Zoom level |
| `x` | integer | Tile X coordinate |
| `y` | integer | Tile Y coordinate |

---

## 📁 Project Structure

```
gurugram-traffic-prevention/
│
├── 📄 README.md                 # This file
├── 📄 config.py                 # Global configuration (centralized)
├── 📄 server.py                 # Combined server + scheduler entry point
├── 📄 .env                      # Environment variables (create this!)
├── 📄 .env.example              # Example environment configuration
├── 📄 requirements.txt          # Python dependencies
│
├── 📁 collector/                # Traffic data collection module
│   ├── 📄 __init__.py
│   ├── 📄 config.py             # Imports from global config
│   ├── 📄 collect_tomtom.py     # TomTom API data fetcher
│   ├── 📄 run_scheduler.py      # Smart scheduler (peak/off-peak)
│   ├── 📄 scheduler.pid         # PID file for daemon mode
│   └── 📁 outputs/              # Collector output files
│       ├── 📄 latest_traffic.json       # Most recent snapshot
│       ├── 📄 traffic_flow_history.csv  # Historical CSV log
│       └── 📁 traffic_snapshots/        # Timestamped JSON files
│           └── 📄 traffic_*.json
│
├── 📁 server/                   # API server module
│   ├── 📄 __init__.py
│   ├── 📄 api.py                # Flask app & route definitions
│   ├── 📄 routing.py            # Route calculation engine
│   ├── 📄 utils.py              # Shared utility functions
│   └── 📁 handlers/             # Modular endpoint handlers
│       ├── 📄 __init__.py
│       ├── 📄 flood_handler.py  # Flood data operations
│       └── 📄 traffic_handler.py # Traffic data operations
│
├── 📁 web/                      # Frontend (served as static files)
│   ├── 📄 index.html            # Main HTML page
│   ├── 📄 app.js                # Application JavaScript
│   ├── 📄 style.css             # Styling
│   └── 📁 data/                 # Data files
│       ├── 📄 clean_roads.geojson       # Road network
│       ├── 📄 flood_roads.geojson       # Static flood roads
│       ├── 📄 ggn_extent.graphml        # Road graph for routing
│       ├── 📄 latest_traffic.json       # Latest traffic (symlink)
│       ├── 📄 points.json               # Traffic hotspot locations
│       ├── 📁 cache/                    # Route & flood cache
│       └── 📁 GEOCODED/                 # Flood timeline GeoJSON
│           └── 📄 D*.geojson            # Format: DYYYYMMDDHHMM.geojson
│
└── 📁 docs/                     # Documentation
    ├── 📄 ARCHITECTURE.md       # System architecture details
    ├── 📄 INDEX.md              # Documentation index
    ├── 📄 QUICKSTART.md         # Quick start guide
    ├── 📄 REFACTORING_SUMMARY.md # Code refactoring notes
    └── 📄 START_HERE.md         # Executive summary
```

---

## 📍 Traffic Monitoring Locations

The system monitors these **25 major intersections** in Gurugram:

| # | Location Name | Coordinates | Zone |
|---|---------------|-------------|------|
| 1 | IFFCO Chowk | 28.4725, 77.0722 | Central |
| 2 | Rajiv Chowk | 28.4596, 77.0266 | Central |
| 3 | Hero Honda Chowk | 28.4250, 76.9876 | South |
| 4 | Kherki Daula Toll Plaza | 28.3875, 76.9456 | South |
| 5 | Signature Tower | 28.4671, 77.0836 | Cyber City |
| 6 | Shankar Chowk / Cyber City | 28.4945, 77.0892 | Cyber City |
| 7 | Sikanderpur Metro | 28.4812, 77.0931 | Cyber City |
| 8 | HUDA City Centre Metro | 28.4595, 77.0722 | Central |
| 9 | Subhash Chowk | 28.4123, 77.0432 | South |
| 10 | Jharsa Chowk | 28.4534, 77.0123 | West |
| 11 | Atul Kataria Chowk | 28.4567, 77.0234 | Central |
| 12 | Mahavir Chowk | 28.4345, 77.0345 | Central |
| 13 | Ghata Chowk | 28.4234, 77.0812 | East |
| 14 | Vatika Chowk (SPR-Sohna Rd) | 28.4012, 77.0645 | South |
| 15 | Badshahpur / Sohna Rd Junction | 28.3923, 77.0534 | South |
| 16 | Ambedkar Chowk | 28.4678, 77.0123 | North |
| 17 | Dundahera (Old Delhi Rd) | 28.4890, 77.0456 | North |
| 18 | Dwarka Expwy-NH48 Cloverleaf | 28.4723, 76.9987 | West |
| 19 | Sector 31 Signal / Market | 28.4534, 77.0456 | Central |
| 20 | Old Gurgaon Bus Stand | 28.4623, 77.0234 | Central |
| 21 | IMT Manesar Junction | 28.3567, 76.9345 | Manesar |
| 22 | Golf Course Rd - One Horizon | 28.4456, 77.0923 | Golf Course |
| 23 | Sector 56/57 - Golf Course Extn | 28.4234, 77.0812 | Golf Course |
| 24 | Sohna Town Entry | 28.2456, 77.0645 | Sohna |
| 25 | Pataudi Rd - Sector 89/90 | 28.4012, 76.9234 | West |

---

## ⚙️ Configuration

### Environment Variables Reference

#### Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_HOST` | `0.0.0.0` | IP address to bind the server |
| `FLASK_PORT` | `8000` | Port number for the server |
| `FLASK_DEBUG` | `False` | Enable Flask debug mode |
| `CORS_ENABLED` | `True` | Enable CORS support |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |

#### API Keys

| Variable | Default | Description |
|----------|---------|-------------|
| `TOMTOM_API_KEY` | _(required)_ | TomTom API key for traffic data |

#### Routing Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `FLOOD_DEPTH_THRESHOLD_M` | `0.3` | Minimum flood depth (meters) to block road |
| `MAX_ROUTE_CACHE_SIZE` | `500` | Maximum number of cached routes |
| `FLOOD_PENALTY` | `1000000.0` | Weight penalty for flooded edges |
| `TRAFFIC_BUFFER_M` | `500` | Traffic data influence radius (meters) |

#### Collector Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `COLLECTOR_INTERVAL_MIN` | `10` | Collection interval (minutes) |
| `PEAK_START_HOUR` | `6` | Peak hours start (24-hour format) |
| `PEAK_END_HOUR` | `21` | Peak hours end (24-hour format) |
| `OFFPEAK_INTERVAL_MIN` | `60` | Off-peak collection interval |

---

## 📈 API Usage Optimization

The traffic collector uses a **smart scheduling strategy** to stay within TomTom's free tier limit of **2,500 API calls/day**:

| Time Period | Collection Interval | Calls/Hour | Daily Calls |
|-------------|---------------------|------------|-------------|
| Peak Hours (6 AM - 9 PM) | 10 minutes | 6 | ~2,160 |
| Off-Peak (9 PM - 6 AM) | 60 minutes | 1 | ~315 |
| **Total** | - | - | **~2,475** |

This ensures you stay within the free tier while maximizing data quality during peak traffic hours.

---

## 🐛 Troubleshooting

### Common Issues

#### 1. CORS Errors in Browser Console

**Symptom:** `Access-Control-Allow-Origin` errors when frontend calls API

**Solution:**
```bash
# Verify CORS is enabled in .env
CORS_ENABLED=True
CORS_ORIGINS=*

# Test CORS preflight
curl -X OPTIONS http://localhost:8000/api/traffic \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" -v
```

---

#### 2. TomTom API Key Not Working

**Symptom:** `401 Unauthorized` or `403 Forbidden` errors

**Solution:**
1. Verify your API key at [TomTom Developer Portal](https://developer.tomtom.com)
2. Check the key is correctly added to `.env`:
   ```env
   TOMTOM_API_KEY=your_actual_key_here
   ```
3. Ensure there are no extra spaces or quotes around the key
4. Restart the server after changing `.env`

---

#### 3. Flood Data Not Loading

**Symptom:** Map shows no flood overlays, API returns empty results

**Solution:**
1. Check flood files exist:
   ```bash
   ls web/data/GEOCODED/
   # Should see D*.geojson files
   ```
2. Verify file naming format: `DYYYYMMDDHHMM.geojson`
3. Check file permissions are readable

---

#### 4. Routing Failures

**Symptom:** Routes return errors or empty results

**Solution:**
1. Verify graph file exists:
   ```bash
   ls web/data/ggn_extent.graphml
   ```
2. Test graph loading:
   ```bash
   python -c "import networkx as nx; G = nx.read_graphml('web/data/ggn_extent.graphml'); print(f'Nodes: {G.number_of_nodes()}, Edges: {G.number_of_edges()}')"
   ```
3. Check graph statistics via API:
   ```bash
   curl http://localhost:8000/api/route/graph-stats
   ```

---

#### 5. Server Won't Start

**Symptom:** Import errors or missing module errors

**Solution:**
```bash
# Reinstall dependencies
pip install --upgrade flask flask-cors waitress requests python-dotenv geopandas shapely networkx

# Check Python version
python --version  # Should be 3.8+

# Verify configuration
python config.py
```

---

#### 6. Traffic Data Not Updating

**Symptom:** Dashboard shows stale traffic data

**Solution:**
1. Check if scheduler is running:
   ```bash
   python collector/run_scheduler.py --status
   ```
2. Manually trigger collection:
   ```bash
   python collector/collect_tomtom.py
   ```
3. Check API key usage at TomTom dashboard

---

## 🔒 Security Considerations

1. **API Key Protection**: Never commit your `.env` file to version control
2. **CORS Configuration**: In production, specify exact allowed origins instead of `*`
3. **Rate Limiting**: Consider adding rate limiting for public deployments
4. **Input Validation**: All API inputs are sanitized to prevent injection attacks

---

## 🚧 Future Enhancements

- [ ] User authentication and saved routes
- [ ] Push notifications for traffic alerts
- [ ] Historical traffic pattern analysis
- [ ] Integration with public transit data
- [ ] Mobile app companion
- [ ] Multi-language support
- [ ] Accessibility improvements (WCAG compliance)

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style

- Python: Follow PEP 8 guidelines
- JavaScript: Use ES6+ features, consistent formatting
- CSS: Use BEM naming convention where applicable

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [TomTom](https://developer.tomtom.com) for traffic data APIs
- [OpenStreetMap](https://www.openstreetmap.org) contributors for map data
- [Leaflet.js](https://leafletjs.com) for the mapping library
- [Chart.js](https://www.chartjs.org) for visualization components
- Gurugram traffic authorities for location data

---

## 📧 Contact

For questions, issues, or suggestions, please:

- Open an issue on GitHub
- Contact the development team

---

<div align="center">

**Made with ❤️ for Gurugram Commuters**

</div>
