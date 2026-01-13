# Quick Start Guide

## 🚀 Setup

### 1. Install Dependencies

```bash
pip install flask flask-cors waitress requests
pip install geopandas shapely osmnx  # Optional for flood-roads intersection
pip install python-dotenv
```

### 2. Environment Configuration

Create `.env` file in project root:

```env
# Server Configuration
FLASK_HOST=127.0.0.1
FLASK_PORT=9110
FLASK_DEBUG=False

# CORS Configuration (FIXED - now configurable!)
CORS_ENABLED=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,*

# API Keys (Required)
TOMTOM_API_KEY=YOUR_API_KEY_HERE

# Optional: Routing Configuration
FLOOD_DEPTH_THRESHOLD_M=0.3
MAX_ROUTE_CACHE_SIZE=500
FLOOD_PENALTY=1000000.0

# Optional: Collector Settings
COLLECTOR_INTERVAL_MIN=10
TIMES_START=2025-07-13T11:25
TIMES_END=2025-07-13T18:17
```

### 3. Verify Configuration

```bash
python config.py
```

You should see the configuration summary printed.

---

## ⚡ Running the Application

### Start the Server

```bash
# Production mode (Waitress WSGI server)
python serve.py

# Development mode (Flask built-in server)
FLASK_DEBUG=True python -m flask run --host=127.0.0.1 --port=9110
```

Server will be running at: **http://localhost:9110**

### Start the Collector (Optional)

**One-time collection:**
```bash
python collector/collect_tomtom.py
```

**Continuous collection (every 10 minutes):**
```bash
python collector/run_scheduler.py
```

---

## 🧪 Testing

### Test CORS Configuration

```bash
# Preflight request
curl -X OPTIONS http://localhost:9110/api/flood \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: GET" \
  -v

# Should return headers:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
# Access-Control-Allow-Headers: Content-Type, Authorization
```

### Test API Endpoints

```bash
# List available flood times
curl http://localhost:9110/api/times

# Get flood data
curl http://localhost:9110/api/flood?time=0

# Get traffic data
curl http://localhost:9110/api/traffic?time=0

# Calculate route
curl "http://localhost:9110/api/route?origin_lat=28.4726&origin_lon=77.0726&dest_lat=28.4595&dest_lon=77.0722&type=shortest"

# Get graph info
curl http://localhost:9110/api/graph-info

# Get cache stats
curl http://localhost:9110/api/cache-stats
```

---

## 🐛 Troubleshooting

### CORS Errors

**Issue:** `Access-Control-Allow-Origin` missing in response

**Solution:**
1. Check `.env` has `CORS_ENABLED=True`
2. Verify origin is in `CORS_ORIGINS` list
3. Include `Content-Type: application/json` header in requests
4. Check browser console for specific error message

### Missing TomTom API Key

**Issue:** `TOMTOM_API_KEY is not set on server`

**Solution:**
1. Get API key from [TomTom Developer Portal](https://developer.tomtom.com)
2. Add to `.env`: `TOMTOM_API_KEY=your_key`
3. Restart server

### Flood Data Not Found

**Issue:** `No flood files found in FLOOD_GEOCODED_DIR`

**Solution:**
1. Verify flood files exist in `web/data/GEOCODED/`
2. Files should be named: `DYYYYMMDDHHMM.geojson`
3. Check path in `config.py` matches your setup

### Routing Engine Issues

**Issue:** Graph not loading or routes failing

**Solution:**
```bash
# Test graph loading
python -c "from server.routing import load_graph; print(load_graph())"
```

Expected output: `MultiDiGraph with X nodes and Y edges`

---

## 📁 Project Structure

```
gurugram-traffic-prevention/
├── .env                          # Configuration (create this!)
├── config.py                     # Global config
├── serve.py                      # Production entry point
├── README.md
├── ARCHITECTURE.md               # Architecture documentation
├── REFACTORING_SUMMARY.md        # Refactoring details
│
├── collector/                    # Traffic data collector
│   ├── config.py
│   ├── collect_tomtom.py
│   ├── run_scheduler.py
│   └── outputs/                  # Collector outputs
│       ├── latest_traffic.json
│       ├── traffic_snapshots/
│       └── ...
│
├── server/                       # API server
│   ├── api.py                    # Main Flask app
│   ├── routing.py                # Route calculation
│   ├── utils.py                  # Utilities
│   └── handlers/                 # Modular handlers
│       ├── flood_handler.py
│       └── traffic_handler.py
│
└── web/                          # Frontend
    ├── index.html
    ├── app.js
    ├── style.css
    └── data/
        ├── clean_roads.geojson
        ├── flood_roads.geojson
        ├── ggn_extent.graphml
        └── GEOCODED/             # Flood timeline
            └── D*.geojson
```

---

## 🔑 Key Changes from Original

| Feature | Before | After |
|---------|--------|-------|
| CORS | Hardcoded | Configurable via .env |
| Config | Scattered files | Centralized config.py |
| Architecture | Monolithic | Modular handlers |
| Collector | Coupled | Independent |
| Bugs | Typo in routing | Fixed |
| Error Handling | Bare excepts | Proper Exception |

---

## 📊 API Response Examples

### /api/times
```json
{
  "count": 5,
  "files": [
    {
      "index": 0,
      "filename": "D202507131125.geojson",
      "label": "2025-07-13 11:25",
      "timestamp": "2025-07-13T11:25:00"
    }
  ]
}
```

### /api/traffic/info
```json
{
  "matched": true,
  "traffic_file": "traffic_2026-01-08T12-47-09.json",
  "traffic_time_ist": "18:17",
  "lag_seconds": 120.5
}
```

### /api/graph-info
```json
{
  "nodes": 45230,
  "edges": 98765,
  "graph_path": "/path/to/ggn_extent.graphml"
}
```

---

## 🚢 Production Deployment

### Using Gunicorn

```bash
# Install
pip install gunicorn

# Run
gunicorn -w 4 -b 0.0.0.0:9110 server.api:app
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
ENV FLASK_HOST=0.0.0.0
ENV FLASK_PORT=9110
ENV CORS_ENABLED=True

EXPOSE 9110
CMD ["python", "serve.py"]
```

### Environment Variables for Production

```env
FLASK_HOST=0.0.0.0
FLASK_PORT=9110
FLASK_DEBUG=False
CORS_ENABLED=True
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
TOMTOM_API_KEY=your_production_key
```

---

## 📚 Documentation Files

- [ARCHITECTURE.md](ARCHITECTURE.md) - Complete architecture reference
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md) - What changed and why
- [config.py](config.py) - Configuration options (with inline documentation)
- [server/handlers/flood_handler.py](server/handlers/flood_handler.py) - Flood handler docs
- [server/handlers/traffic_handler.py](server/handlers/traffic_handler.py) - Traffic handler docs

---

## ✅ Verification Checklist

- [ ] `.env` file created with required variables
- [ ] `TOMTOM_API_KEY` is set
- [ ] Server starts without errors: `python serve.py`
- [ ] API responds: `curl http://localhost:9110/api/times`
- [ ] CORS headers present: Check network tab in browser
- [ ] Flood data files exist: `ls web/data/GEOCODED/`
- [ ] Collector can run: `python collector/collect_tomtom.py`

---

## 🆘 Getting Help

1. Check logs for specific error messages
2. Review [ARCHITECTURE.md](ARCHITECTURE.md) troubleshooting section
3. Verify all required files exist
4. Check `.env` configuration
5. Run `python config.py` to verify setup

---

**Happy coding! 🚀**

