# Architecture Refactoring - Documentation

## Overview

The codebase has been refactored into a modular, maintainable architecture with proper separation of concerns. Key improvements include:

1. **Fixed CORS Issues** - Properly configured CORS with support for multiple origins
2. **Global Configuration** - Centralized config.py at project root
3. **Modular Server Structure** - Clean separation of handlers and utilities
4. **Independent Collector** - Collector module remains separate, with outputs used by the main server
5. **Bug Fixes** - Fixed typos and improved error handling

---

## Project Structure

```
gurugram-traffic-prevention/
├── config.py                    # GLOBAL configuration (NEW)
├── serve.py                     # Production server entry point (UPDATED)
├── .env                         # Environment variables (API keys, etc.)
├── README.md
│
├── collector/
│   ├── __init__.py
│   ├── config.py               # Imports from global config.py
│   ├── collect_tomtom.py       # Independent traffic data collector
│   ├── run_scheduler.py        # Scheduled collection runner
│   └── outputs/                # Collector output files
│       ├── latest_traffic.json
│       ├── traffic_snapshots/
│       ├── *.geojson
│       └── ... (other outputs)
│
├── server/
│   ├── __init__.py
│   ├── api.py                  # Main Flask app (REFACTORED)
│   ├── routing.py              # Route calculation engine (UPDATED)
│   ├── utils.py                # Shared utilities (NEW)
│   └── handlers/               # Modular endpoint handlers (NEW)
│       ├── __init__.py
│       ├── flood_handler.py    # Flood data endpoints
│       └── traffic_handler.py  # Traffic data endpoints
│
└── web/
    ├── app.js                  # Frontend JavaScript
    ├── index.html              # Main HTML file
    ├── style.css               # Styling
    └── data/
        ├── clean_roads.geojson
        ├── flood_roads.geojson
        ├── ggn_extent.graphml
        ├── latest_traffic.json
        └── GEOCODED/           # Flood timeline GeoJSON files
            └── D*.geojson
```

---

## Key Features

### 1. CORS Configuration (FIXED)

**Location:** [config.py](config.py#L25-L29) and [server/api.py](server/api.py#L35-L52)

The CORS issue has been fixed with proper configuration:

```python
# In config.py
CORS_ENABLED = os.getenv("CORS_ENABLED", "True").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")

# In server/api.py
if global_config.CORS_ENABLED:
    cors_config = {
        "origins": global_config.CORS_ORIGINS if global_config.CORS_ORIGINS != ["*"] else "*",
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True,
        "max_age": 3600
    }
    CORS(app, resources={r"/api/*": cors_config})
```

**Configuration via .env:**
```
CORS_ENABLED=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,*
```

### 2. Global Configuration

**Location:** [config.py](config.py)

Centralized configuration for the entire application:

```python
# Server Configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 9110
FLASK_DEBUG = False

# CORS
CORS_ENABLED = True
CORS_ORIGINS = ["*"]

# API Keys
TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY", "")

# Data Paths
FLOOD_GEOCODED_DIR = WEB_DIR / "data" / "GEOCODED"
TRAFFIC_SNAPSHOTS_DIR = COLLECTOR_OUTPUTS / "traffic_snapshots"

# Monitoring Points
MONITOR_POINTS = [...]

# Routing Configuration
FLOOD_DEPTH_THRESHOLD_M = 0.3
MAX_ROUTE_CACHE_SIZE = 500
```

### 3. Modular Server Structure

**Handlers** ([server/handlers/](server/handlers/)):

- **flood_handler.py**: Flood data retrieval and processing
  - `list_flood_files()` - List available flood data
  - `resolve_flood_path_by_index()` - Find flood file by index
  - `get_flooded_roads()` - Calculate flooded road segments

- **traffic_handler.py**: Traffic data management
  - `find_nearest_traffic_snapshot()` - Find traffic by timestamp
  - `get_traffic_snapshot()` - Retrieve traffic data
  - `get_traffic_info()` - Get traffic metadata

**Utilities** ([server/utils.py](server/utils.py)):

- `find_roads_file()` - Locate roads GeoJSON
- `find_graph_file()` - Locate graph file
- `atomic_write_json()` - Safe JSON writing
- `atomic_read_json()` - Safe JSON reading

### 4. Collector Component (Independent)

**Location:** [collector/](collector/)

The collector remains independent and is used to:
- Fetch traffic data from TomTom API at regular intervals
- Store traffic snapshots in [collector/outputs/traffic_snapshots/](collector/outputs/traffic_snapshots/)
- Maintain a [collector/outputs/latest_traffic.json](collector/outputs/latest_traffic.json)

**Configuration:**
- [collector/config.py](collector/config.py) imports from global config
- Run independently: `python collector/collect_tomtom.py`
- Scheduled collection: `python collector/run_scheduler.py`

### 5. Bug Fixes

#### Fixed Bugs:

1. **Typo in routing.py (line 65)**
   - Before: `global _graph, _graphml_path_usedo`
   - After: `global _graph, _graphml_path_used`

2. **CORS Hardcoded to accept all origins**
   - Before: `CORS(app)` (no configuration)
   - After: Proper CORS configuration with `resources` parameter

3. **Bare except clauses replaced**
   - Before: `except:`
   - After: `except Exception:` (proper exception handling)

4. **Missing return type handling**
   - Fixed flood data return to properly return JSON content

---

## Environment Variables

Create a `.env` file in the project root:

```env
# Server Configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=9110
FLASK_DEBUG=False

# CORS Configuration
CORS_ENABLED=True
CORS_ORIGINS=*

# API Keys
TOMTOM_API_KEY=YOUR_TOMTOM_API_KEY_HERE

# Routing Configuration
FLOOD_DEPTH_THRESHOLD_M=0.3
MAX_ROUTE_CACHE_SIZE=500
FLOOD_PENALTY=1000000.0

# Collector
COLLECTOR_INTERVAL_MIN=10

# Frontend Time Filter
TIMES_START=2025-07-13T11:25
TIMES_END=2025-07-13T18:17
```

---

## API Endpoints

### Flood Data
- `GET /api/times` - List available flood time periods
- `GET /api/flood` - Get flood polygons GeoJSON
- `GET /api/flood-roads` - Get flooded road segments

### Traffic Data
- `GET /api/traffic` - Get traffic snapshot
- `GET /api/traffic/info` - Get traffic metadata
- `POST /api/traffic/refresh` - Refresh traffic endpoint

### Routing
- `GET /api/route` - Calculate optimal route
- `GET /api/graph-info` - Get graph statistics
- `GET /api/cache-stats` - Get cache performance stats

### TomTom Proxies
- `GET /api/tomtom/geocode` - Geocode search query
- `GET /api/tomtom/traffic-tiles/{z}/{x}/{y}` - Traffic tiles

---

## Running the Application

### Development Server

```bash
# Terminal 1: Run the server
python serve.py

# Terminal 2: Run the collector (optional)
python collector/collect_tomtom.py

# Or run scheduler for continuous collection
python collector/run_scheduler.py
```

### Production Server (Waitress)

```bash
# Using serve.py with Waitress
python serve.py
```

### Flask Development Mode

```bash
export FLASK_DEBUG=True
python -m flask run --host=127.0.0.1 --port=9110
```

---

## Configuration Changes

### Before
- CORS: Hardcoded, no configuration
- Config: Scattered across multiple files
- Paths: Duplicated in multiple modules
- Collector: Tightly coupled to API

### After
- CORS: Configurable via environment and global config
- Config: Centralized in [config.py](config.py)
- Paths: Defined once in config, reused everywhere
- Collector: Independent, outputs consumed by API
- Handlers: Modular, easy to extend
- Utilities: Shared across modules

---

## Testing Configuration

Test the CORS configuration:

```bash
# Test CORS preflight request
curl -X OPTIONS http://localhost:9110/api/flood \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Expected response headers:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
# Access-Control-Allow-Headers: Content-Type, Authorization
```

---

## Future Improvements

1. **Async Handlers** - Use async/await for I/O-bound operations
2. **Database Integration** - Store traffic history in database
3. **API Documentation** - Add Swagger/OpenAPI documentation
4. **Unit Tests** - Comprehensive test suite
5. **Logging** - Structured logging with rotating file handlers
6. **Caching Layers** - Redis for distributed caching
7. **Rate Limiting** - Implement rate limiting for API endpoints

---

## Troubleshooting

### CORS Errors
1. Check `CORS_ENABLED` is `True` in .env
2. Verify origin is in `CORS_ORIGINS` list
3. Ensure `Content-Type` header is included in requests

### Missing Data Files
1. Check paths in [config.py](config.py) match your setup
2. Run `python config.py` to see configuration summary
3. Verify flood files exist in `web/data/GEOCODED/`

### Collector Issues
1. Set `TOMTOM_API_KEY` in .env
2. Check collector outputs: `collector/outputs/`
3. Verify network access to TomTom API

### Routing Errors
1. Ensure graph file exists (ggn_extent.graphml)
2. Check road GeoJSON is in web/data/
3. Run `python server/routing.py` to test loading

