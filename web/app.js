console.log("APP.JS LOADED:", new Date().toISOString());

/* =========================
   CONFIG
========================= */
const API_BASE = "http://localhost:8000";

const TIMES_URL = `${API_BASE}/api/times`;
const FLOOD_POLY_URL = (i) => `${API_BASE}/api/flood?time=${encodeURIComponent(i)}`;
const FLOOD_ROADS_URL = (i) => `${API_BASE}/api/flood-roads?time=${encodeURIComponent(i)}`;
const TRAFFIC_SNAPSHOT_URL = (timeIdx = null) =>
  timeIdx !== null ? `${API_BASE}/api/traffic?time=${encodeURIComponent(timeIdx)}` : `${API_BASE}/api/traffic`;

// Preset locations
const PRESET_LOCATIONS = {
  iffco: { name: "IFFCO Chowk", lat: 28.4726, lon: 77.0726 },
  mgroad: { name: "MG Road", lat: 28.4795, lon: 77.0806 },
  cyberhub: { name: "Cyber Hub", lat: 28.4947, lon: 77.0897 },
  golfcourse: { name: "Golf Course Rd", lat: 28.4503, lon: 77.0972 },
  sohna: { name: "Sohna Road", lat: 28.4073, lon: 77.046 },
  nh48: { name: "NH-48 (Ambience)", lat: 28.5052, lon: 77.097 },
  rajiv: { name: "Rajiv Chowk", lat: 28.4691, lon: 77.0366 },
  huda: { name: "Huda City Centre", lat: 28.4595, lon: 77.0722 },
  sector56: { name: "Sector 56", lat: 28.4244, lon: 77.107 },
  manesar: { name: "Manesar Rd", lat: 28.354, lon: 76.944 }
};

/* =========================
   HELPERS
========================= */
function formatTimeNice(ts) {
  if (!ts) return null;
  const d = new Date(ts);
  if (Number.isNaN(d.getTime())) return String(ts);
  return d.toLocaleString();
}

function colorBySpeedRatio(sr) {
  if (sr >= 0.85) return "#2ecc71";
  if (sr >= 0.65) return "#f39c12";
  return "#e74c3c";
}

function getFloodMode() {
  const checked = document.querySelector('input[name="floodMode"]:checked');
  return checked ? checked.value : "roads"; // roads | polygons
}

// getRouteMode removed - using checkboxes now via getSelectedRouteTypes()

/* =========================
   MAP + PANES
========================= */
const map = L.map("map", { zoomControl: true }).setView([28.4595, 77.0266], 13);

map.createPane("basePane");
map.getPane("basePane").style.zIndex = 200;

map.createPane("trafficPane");
map.getPane("trafficPane").style.zIndex = 450;

map.createPane("floodPane");
map.getPane("floodPane").style.zIndex = 455;  // Flood layer below routes

map.createPane("routePane");
map.getPane("routePane").style.zIndex = 460;  // Routes ABOVE flood layer

map.createPane("markerPane");
map.getPane("markerPane").style.zIndex = 500;

/* =========================
   BASEMAPS
========================= */
const ATTR_OSM = '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors';
const ATTR_CARTO =
  '&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>';

// OSM Standard
const osmStandard = L.tileLayer(
  "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  { maxZoom: 19, attribution: ATTR_OSM, pane: "basePane" }
);

// Carto Light
const baseLight = L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png",
  { maxZoom: 19, attribution: ATTR_CARTO, pane: "basePane" }
);

// Carto Dark
const baseDark = L.tileLayer(
  "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
  { maxZoom: 19, attribution: ATTR_CARTO, pane: "basePane" }
);

// Satellite (ESRI)
const satellite = L.tileLayer(
  "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
  { maxZoom: 19, attribution: "ESRI", pane: "basePane" }
);

// Google Maps layers
const googleStreets = L.tileLayer(
  "https://{s}.google.com/vt/lyrs=m&x={x}&y={y}&z={z}",
  { maxZoom: 20, subdomains: ["mt0", "mt1", "mt2", "mt3"], attribution: "Google", pane: "basePane" }
);

const googleSatellite = L.tileLayer(
  "https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
  { maxZoom: 20, subdomains: ["mt0", "mt1", "mt2", "mt3"], attribution: "Google", pane: "basePane" }
);

const googleHybrid = L.tileLayer(
  "https://{s}.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
  { maxZoom: 20, subdomains: ["mt0", "mt1", "mt2", "mt3"], attribution: "Google", pane: "basePane" }
);

const googleTerrain = L.tileLayer(
  "https://{s}.google.com/vt/lyrs=p&x={x}&y={y}&z={z}",
  { maxZoom: 20, subdomains: ["mt0", "mt1", "mt2", "mt3"], attribution: "Google", pane: "basePane" }
);

// Add default and layer control
googleStreets.addTo(map);  // Default to Google Streets

L.control.layers({
  "OSM Standard": osmStandard,
  "Light (Carto)": baseLight,
  "Dark (Carto)": baseDark,
  "Satellite (ESRI)": satellite,
  "Google Streets": googleStreets,
  "Google Satellite": googleSatellite,
  "Google Hybrid": googleHybrid,
  "Google Terrain": googleTerrain
}, null, { position: "topright", collapsed: true }).addTo(map);

/* =========================
   LIVE TRAFFIC TILES
========================= */
const trafficTiles = L.tileLayer(`${API_BASE}/api/tomtom/traffic-tiles/{z}/{x}/{y}`, {
  opacity: 0.75,
  maxZoom: 19,
  pane: "trafficPane"
});

/* =========================
   ROAD NETWORK OVERLAY
========================= */
let roadNetworkLayer = null;

async function loadRoadNetworkOverlay() {
  if (roadNetworkLayer) return; // Already loaded

  try {
    console.log("[Roads] Loading road network overlay...");
    const res = await fetch("./data/clean_roads.geojson");
    if (!res.ok) throw new Error(`Failed to load: ${res.status}`);

    const geojson = await res.json();

    roadNetworkLayer = L.geoJSON(geojson, {
      pane: "basePane",
      style: {
        color: "#000000",  // black roads
        weight: 1.5,
        opacity: 0.6
      },
      // Filter to LineStrings only
      filter: (feature) => {
        const t = feature?.geometry?.type;
        return t === "LineString" || t === "MultiLineString";
      }
    });

    console.log("[Roads] Road network layer ready");
  } catch (err) {
    console.error("[Roads] Error loading road network:", err);
  }
}

function toggleRoadNetwork(show) {
  if (show) {
    if (!roadNetworkLayer) {
      loadRoadNetworkOverlay().then(() => {
        if (roadNetworkLayer) roadNetworkLayer.addTo(map);
      });
    } else {
      if (!map.hasLayer(roadNetworkLayer)) roadNetworkLayer.addTo(map);
    }
  } else {
    if (roadNetworkLayer && map.hasLayer(roadNetworkLayer)) {
      map.removeLayer(roadNetworkLayer);
    }
  }
}

/* =========================
   FLOOD TIMELINE + FLOOD LAYER
========================= */
let floodLayer = null;
let floodTimes = [];
let currentFloodIndex = 0;

function setFloodTimelineStatus(msg) {
  const el = document.getElementById("floodTimelineStatus");
  if (el) el.textContent = msg || "";
}

function setFloodTimeLabel(idx) {
  const el = document.getElementById("floodTimeLabel");
  const elScenario = document.getElementById("scenarioFloodTime"); // New panel label

  const item = floodTimes.find((x) => Number(x.index) === Number(idx));
  const text = item ? `Index ${item.index} • ${item.label}` : `Index ${idx}`;

  if (el) el.textContent = text;

  // Update Scenario Panel as well
  if (elScenario) {
    elScenario.textContent = item ? item.label : `Index ${idx}`;
  }
}

async function loadFloodTimeline() {
  try {
    setFloodTimelineStatus("Flood timeline: loading…");

    const res = await fetch(TIMES_URL, { cache: "no-store" });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data?.error || `Times fetch failed: ${res.status}`);
    }

    floodTimes = Array.isArray(data.files) ? data.files : [];

    const slider = document.getElementById("floodTimeSlider");
    if (!slider) {
      setFloodTimelineStatus("Flood timeline: slider element not found");
      return;
    }

    if (floodTimes.length === 0) {
      slider.min = "0";
      slider.max = "0";
      slider.value = "0";
      currentFloodIndex = 0;
      setFloodTimelineStatus("Flood timeline: no snapshots found");
      setFloodTimeLabel(0);
      return;
    }

    const indices = floodTimes.map((x) => Number(x.index)).filter(Number.isFinite);
    const minIdx = Math.min(...indices);
    const maxIdx = Math.max(...indices);

    slider.min = String(minIdx);
    slider.max = String(maxIdx);
    slider.value = String(minIdx);

    currentFloodIndex = minIdx;
    setFloodTimeLabel(currentFloodIndex);

    setFloodTimelineStatus(`Flood timeline: loaded ${floodTimes.length} snapshots`);

    await loadFloodLayerByIndex(currentFloodIndex);
  } catch (err) {
    console.error("Error loading flood timeline:", err);
    setFloodTimelineStatus("Flood timeline: failed to load (check console /api/times)");
  }
}

async function loadFloodLayerByIndex(idx) {
  try {
    currentFloodIndex = Number(idx);
    setFloodTimeLabel(currentFloodIndex);

    const mode = getFloodMode();
    const url = mode === "polygons" ? FLOOD_POLY_URL(currentFloodIndex) : FLOOD_ROADS_URL(currentFloodIndex);

    const res = await fetch(url, { cache: "no-store" });
    const geojson = await res.json();

    if (!res.ok) throw new Error(geojson?.error || `Flood fetch failed: ${res.status}`);
    if (geojson?.error) throw new Error(geojson.error);

    if (floodLayer && map.hasLayer(floodLayer)) map.removeLayer(floodLayer);

    floodLayer = L.geoJSON(geojson, {
      pane: "floodPane",

      // remove pin markers (Point features)
      filter: (feature) => {
        const t = feature?.geometry?.type;
        return t !== "Point" && t !== "MultiPoint";
      },

      // extra safety
      pointToLayer: () => null,

      // Solid blue for ALL flooded roads
      style: {
        color: "#3b82f6",  // blue
        weight: 6,
        opacity: 0.8
      }
    });


    if (document.getElementById("toggleFlood")?.checked) floodLayer.addTo(map);

    console.log("✓ Flood layer loaded:", { index: currentFloodIndex, mode });

    // Update traffic sync info
    updateTrafficSyncInfo(currentFloodIndex);
  } catch (err) {
    console.error("Error loading flood layer:", err);
  }
}

// Update traffic sync info indicator
async function updateTrafficSyncInfo(floodIndex) {
  const el = document.getElementById("trafficSyncInfo");
  if (!el) return;

  try {
    const res = await fetch(`${API_BASE}/api/traffic/info?time=${floodIndex}`);
    const data = await res.json();

    if (data.matched && data.traffic_time_ist) {
      el.textContent = `📍 Traffic synced to: ${data.traffic_time_ist} IST`;
      el.style.color = "#16a34a";  // green
    } else {
      el.textContent = `⚠️ Traffic: using latest snapshot`;
      el.style.color = "#f59e0b";  // amber
    }
  } catch (err) {
    el.textContent = `⚠️ Traffic sync info unavailable`;
    el.style.color = "#dc2626";  // red
  }
}

/* =========================
   TRAFFIC SNAPSHOT POINTS
========================= */
let trafficSnapshot = null;
let trafficPointMarkers = [];

function clearTrafficPointMarkers() {
  trafficPointMarkers.forEach((m) => map.removeLayer(m));
  trafficPointMarkers = [];
}

async function loadTrafficSnapshot(timeIdx = null) {
  const statusEl = document.getElementById("snapshotStatus");
  try {
    if (statusEl) statusEl.textContent = "Traffic snapshot: loading...";

    const res = await fetch(TRAFFIC_SNAPSHOT_URL(timeIdx), { cache: "no-store" });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || `Traffic snapshot fetch failed: ${res.status}`);

    trafficSnapshot = data;
    clearTrafficPointMarkers();

    const points = trafficSnapshot.points || [];
    const updated = trafficSnapshot.generated_at_local || formatTimeNice(trafficSnapshot.generated_at_utc);

    if (statusEl) {
      const timeInfo = timeIdx !== null ? ` (synced to timeline index ${timeIdx})` : "";
      statusEl.textContent = updated
        ? `Traffic: ${updated} (${points.length} pts)${timeInfo}`
        : `Traffic: loaded (${points.length} pts)${timeInfo}`;
    }

    points.forEach((p) => {
      const sr = Number(p.speed_ratio ?? 0);
      const color = colorBySpeedRatio(sr);

      const lat = Number(p.lat ?? p.query_lat);
      const lon = Number(p.lon ?? p.query_lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

      const cur = p.currentSpeed_kmph ?? p.currentSpeed ?? "N/A";
      const ff = p.freeFlowSpeed_kmph ?? p.freeFlowSpeed ?? "N/A";
      const ptUpdated = p.timestamp_local || formatTimeNice(p.timestamp_utc) || "N/A";

      const marker = L.circleMarker([lat, lon], {
        radius: 12,
        fillColor: color,
        color: "#000",
        weight: 2,
        opacity: 1,
        fillOpacity: 0.9,
        pane: "markerPane"
      });

      marker.bindPopup(
        `<b>${p.name ?? "Traffic point"}</b><br/>
         <span style="color:#555">Updated: ${ptUpdated}</span><br/>
         Speed ratio: ${(sr * 100).toFixed(1)}%<br/>
         Current speed: ${cur} km/h<br/>
         Free-flow speed: ${ff} km/h`
      );

      marker.addTo(map);
      trafficPointMarkers.push(marker);
    });

    console.log("✓ Traffic snapshot markers loaded:", trafficPointMarkers.length, timeIdx !== null ? `(synced to index ${timeIdx})` : "");
  } catch (err) {
    console.error("Error loading traffic snapshot:", err);
    if (statusEl) statusEl.textContent = "Traffic snapshot: failed to load";
  }
}

async function refreshTraffic() {
  const statusEl = document.getElementById("snapshotStatus");
  try {
    if (statusEl) statusEl.textContent = "Refreshing traffic...";
    await fetch(`${API_BASE}/api/traffic/refresh`, { method: "POST" }).catch(() => { });
    await loadTrafficSnapshot();
  } catch (err) {
    console.error("Refresh traffic failed:", err);
    if (statusEl) statusEl.textContent = "Traffic snapshot: refresh failed";
  }
}

/* =========================
   SEARCH
========================= */
let searchMarker = null;

async function handleSearch() {
  const searchTerm = document.getElementById("searchInput")?.value.trim();
  if (!searchTerm) return alert("Please enter a location.");

  try {
    const res = await fetch(`${API_BASE}/api/tomtom/geocode?search=${encodeURIComponent(searchTerm)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data?.error || "Failed to fetch geocode data");

    if (!data.results?.length) return alert("Location not found.");

    const { lat, lon } = data.results[0].position;

    if (searchMarker) map.removeLayer(searchMarker);
    searchMarker = L.marker([lat, lon]).addTo(map).bindPopup(searchTerm).openPopup();
    map.setView([lat, lon], 14);

    setTimeout(restoreLayerVisibility, 150);
  } catch (err) {
    console.error("Search error:", err);
    alert("Error searching location.");
  }
}

/* =========================
   ROUTING - Multi-route comparison
========================= */
// Route colors config
const ROUTE_COLORS = {
  shortest: "#8b5cf6",    // purple
  fastest: "#6a340dff",     // brown
  flood_avoid: "#006400", // dark green (changed for visibility)
  smart: "#000000"        // black
};

const ROUTE_WEIGHTS = {
  shortest: 6,
  fastest: 5,
  flood_avoid: 5,
  smart: 7
};

// Route layers for each type
let routeLayers = {
  shortest: null,
  fastest: null,
  flood_avoid: null,
  smart: null
};

// Flooded segment overlay layers
let floodedOverlayLayers = {
  flood_avoid: null,
  smart: null
};

let originMarker = null;
let destMarker = null;

let routeOrigin = null;
let routeDestination = null;
let clickMode = null;

function setRouteStatus(msg) {
  const el = document.getElementById("routeStatus");
  if (el) el.textContent = msg || "";
}

function clearRoutes() {
  // Remove all route layers
  Object.keys(routeLayers).forEach(key => {
    if (routeLayers[key]) {
      map.removeLayer(routeLayers[key]);
      routeLayers[key] = null;
    }
  });

  // Remove flooded overlay layers
  Object.keys(floodedOverlayLayers).forEach(key => {
    if (floodedOverlayLayers[key]) {
      map.removeLayer(floodedOverlayLayers[key]);
      floodedOverlayLayers[key] = null;
    }
  });

  if (originMarker) map.removeLayer(originMarker);
  if (destMarker) map.removeLayer(destMarker);

  originMarker = null;
  destMarker = null;
  routeOrigin = null;
  routeDestination = null;
  clickMode = null;
  document.body.style.cursor = "default";
  setRouteStatus("");
}

function setOriginMode() {
  clickMode = "origin";
  document.body.style.cursor = "crosshair";
  setRouteStatus("Click on map to set ORIGIN");
}

function setDestinationMode() {
  clickMode = "destination";
  document.body.style.cursor = "crosshair";
  setRouteStatus("Click on map to set DESTINATION");
}

// Get selected route types from checkboxes
function getSelectedRouteTypes() {
  const types = [];
  if (document.getElementById("routeShortest")?.checked) types.push("shortest");
  if (document.getElementById("routeTraffic")?.checked) types.push("fastest");
  if (document.getElementById("routeFlood")?.checked) types.push("flood_avoid");
  if (document.getElementById("routeSmart")?.checked) types.push("smart");
  return types;
}

// Add a single route layer with specific color
function addSingleRouteLayer(routeType, geojson) {
  // Remove existing layer for this type
  if (routeLayers[routeType]) {
    map.removeLayer(routeLayers[routeType]);
    routeLayers[routeType] = null;
  }

  // Remove existing flooded overlay for this type
  if (floodedOverlayLayers[routeType]) {
    map.removeLayer(floodedOverlayLayers[routeType]);
    floodedOverlayLayers[routeType] = null;
  }

  const color = ROUTE_COLORS[routeType] || "#3b82f6";
  const weight = ROUTE_WEIGHTS[routeType] || 5;

  // Find the main route feature (first one without segment_type)
  const features = geojson.features || [];
  const mainFeature = features.find(f => !f.properties?.segment_type) || features[0];
  const floodedFeature = features.find(f => f.properties?.segment_type === "flooded_passable");

  // Render main route
  if (mainFeature) {
    routeLayers[routeType] = L.geoJSON({ type: "FeatureCollection", features: [mainFeature] }, {
      pane: "routePane",
      style: {
        color: color,
        weight: weight,
        opacity: 0.85,
        lineCap: "round",
        lineJoin: "round"
      }
    }).addTo(map);
  }

  // Render flooded segments overlay (green dashed)
  if (floodedFeature && (routeType === "flood_avoid" || routeType === "smart")) {
    floodedOverlayLayers[routeType] = L.geoJSON({ type: "FeatureCollection", features: [floodedFeature] }, {
      pane: "routePane",
      style: {
        color: "#16a34a",  // green
        weight: weight + 2,
        opacity: 0.9,
        dashArray: "8, 8",
        lineCap: "round",
        lineJoin: "round"
      }
    }).addTo(map);

    // Add popup to flooded overlay
    const floodDistKm = (floodedFeature.properties.distance_m / 1000).toFixed(2);
    floodedOverlayLayers[routeType].bindPopup(
      `<b>🌊 Shallow Flood Crossing</b><br/>` +
      `Distance: ${floodDistKm} km<br/>` +
      `<span style="color:#16a34a">Depth ≤ 0.3m - Safe to pass</span>`
    );
  }

  const props = geojson.properties || {};
  const distKm = props.distance_m != null ? (props.distance_m / 1000).toFixed(2) : "N/A";
  const etaMin = props.eta_s != null ? (props.eta_s / 60).toFixed(1) : null;

  // Calculate avg speed: distance (km) / time (hours)
  let avgSpeedKmh = "N/A";
  if (props.distance_m != null && props.eta_s != null && props.eta_s > 0) {
    avgSpeedKmh = ((props.distance_m / 1000) / (props.eta_s / 3600)).toFixed(1);
  }

  // Build popup content
  let popupContent =
    `<b>${routeType.replace("_", " ").toUpperCase()}</b><br/>` +
    `Distance: ${distKm} km${etaMin ? `<br/>ETA: ${etaMin} min` : ""}` +
    `<br/>Avg Speed: ${avgSpeedKmh} km/h`;

  // Add flood info for flood_avoid and smart routes
  if ((routeType === "flood_avoid" || routeType === "smart") && props.has_flood) {
    const floodedDist = props.flooded_distance_m != null ? (props.flooded_distance_m / 1000).toFixed(2) : "?";
    popupContent += `<br/><span style="color:#16a34a">🌊 Uses ${floodedDist} km shallow flood (≤0.3m)</span>`;
  } else if ((routeType === "flood_avoid" || routeType === "smart") && !props.has_flood) {
    popupContent += `<br/><span style="color:#16a34a">✅ No flooded roads</span>`;
  }

  if (routeLayers[routeType]) {
    routeLayers[routeType].bindPopup(popupContent);
  }
}

// Fetch a single route from backend
async function fetchRoute(routeType) {
  const url =
    `${API_BASE}/api/route?` +
    `origin_lat=${routeOrigin.lat}&origin_lon=${routeOrigin.lng}` +
    `&dest_lat=${routeDestination.lat}&dest_lon=${routeDestination.lng}` +
    `&type=${encodeURIComponent(routeType)}` +
    `&flood_time=${encodeURIComponent(String(currentFloodIndex))}`;

  try {
    const res = await fetch(url);
    const geojson = await res.json();
    if (!res.ok || geojson?.error) {
      console.warn(`Route ${routeType} failed:`, geojson?.error || res.status);
      return null;
    }
    return { routeType, geojson };
  } catch (err) {
    console.error(`Route ${routeType} error:`, err);
    return null;
  }
}

// Calculate all selected route types
async function calculateAllRoutes() {
  if (!routeOrigin || !routeDestination) return;

  const selectedTypes = getSelectedRouteTypes();
  if (selectedTypes.length === 0) {
    setRouteStatus("Select at least one route type");
    return;
  }

  setRouteStatus(`Calculating ${selectedTypes.length} route(s)...`);

  // Clear routes not selected
  Object.keys(routeLayers).forEach(key => {
    if (!selectedTypes.includes(key) && routeLayers[key]) {
      map.removeLayer(routeLayers[key]);
      routeLayers[key] = null;
    }
  });

  // Fetch all selected routes in parallel
  const promises = selectedTypes.map(type => fetchRoute(type));
  const results = await Promise.all(promises);

  let successCount = 0;

  // Calculate stats for all routes to populate comparison table
  updateRouteComparison(routeOrigin, routeDestination);

  results.forEach(result => {
    if (result && result.geojson) {
      addSingleRouteLayer(result.routeType, result.geojson);
      successCount++;
    }
  });

  if (successCount > 0) {
    setRouteStatus(`${successCount} route(s) ready`);
    setTimeout(() => setRouteStatus(""), 2000);
  } else {
    setRouteStatus("No routes found");
  }
}

// Helper to get lon from latlng object (handles .lng vs .lon)
function getLon(obj) {
  return obj.lng !== undefined ? obj.lng : obj.lon;
}

// Fetch comparison data for all 4 types without drawing them all
async function updateRouteComparison(origin, dest) {
  const table = document.getElementById("routeComparisonPanel");
  const tbody = document.getElementById("routeComparisonBody");
  if (!table || !tbody) return;

  table.style.display = "block";
  tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#94a3b8;">Calculating...</td></tr>';

  const types = [
    { id: "shortest", label: "Shortest" },
    { id: "fastest", label: "Fastest" },
    { id: "flood_avoid", label: "Flood-Avoid" },
    { id: "smart", label: "Smart" }
  ];

  try {
    const oLon = getLon(origin);
    const dLon = getLon(dest);

    // Use Promise.allSettled so if one fails, others still show
    const promises = types.map(t =>
      fetch(`${API_BASE}/api/route?origin_lat=${origin.lat}&origin_lon=${oLon}&dest_lat=${dest.lat}&dest_lon=${dLon}&type=${t.id}&flood_time=${currentFloodIndex}`)
        .then(res => {
          if (!res.ok) throw new Error(res.statusText);
          return res.json();
        })
        .then(data => ({ type: t, data: data, success: true }))
        .catch(err => ({ type: t, error: err, success: false }))
    );

    const results = await Promise.all(promises);

    tbody.innerHTML = ""; // Clear loader

    results.forEach(res => {
      const type = res.type;

      const tr = document.createElement("tr");
      tr.style.borderBottom = "1px solid #f1f5f9";

      if (!res.success) {
        tr.innerHTML = `
            <td style="padding: 6px; font-weight: 500;">${type.label}</td>
            <td colspan="3" style="padding: 6px; color: #ef4444;">Failed</td>
         `;
        tbody.appendChild(tr);
        return;
      }

      const props = res.data.properties;

      // Status icon
      let statusIcon = "✅";
      let statusText = "OK";
      let etaMin = Math.round(props.eta_s / 60);

      if (props.has_flood) {
        statusIcon = "⚠️";
        statusText = "Flooded";
      } else if (type.id === "fastest" && props.eta_s > props.distance_m / 10) {
        statusIcon = "🚗";
        statusText = "Traffic";
      } else if (type.id === "smart") {
        statusIcon = "⭐";
        statusText = "Best";
      }

      // Format row
      tr.innerHTML = `
        <td style="padding: 6px; font-weight: 500;">${type.label}</td>
        <td style="padding: 6px;">${(props.distance_m / 1000).toFixed(1)} km</td>
        <td style="padding: 6px;">${etaMin} min</td>
        <td style="padding: 6px; font-size: 11px;">${statusIcon} ${statusText}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Comparison fatal error:", err);
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center; color:#ef4444;">Error updating table</td></tr>';
  }
}


// Backwards compatible single route calculation
async function calculateRouteSingle() {
  await calculateAllRoutes();
}

// Map click → set origin/destination
map.on("click", (e) => {
  if (!clickMode) return;

  const latlng = e.latlng;

  if (clickMode === "origin") {
    routeOrigin = latlng;
    if (originMarker) map.removeLayer(originMarker);
    // Google Maps style red pin marker
    const originIcon = L.divIcon({
      className: 'custom-marker',
      html: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 24 30"><path fill="#22c55e" stroke="#fff" stroke-width="1" d="M12 0C5.4 0 0 5.4 0 12c0 7.2 12 18 12 18s12-10.8 12-18C24 5.4 18.6 0 12 0z"/><circle fill="#fff" cx="12" cy="10" r="4"/></svg>`,
      iconSize: [32, 40],
      iconAnchor: [16, 40],
      popupAnchor: [0, -40]
    });
    originMarker = L.marker(latlng, { icon: originIcon, pane: "markerPane" }).addTo(map).bindPopup("Origin").openPopup();
  }

  if (clickMode === "destination") {
    routeDestination = latlng;
    if (destMarker) map.removeLayer(destMarker);
    // Google Maps style red pin marker
    const destIcon = L.divIcon({
      className: 'custom-marker',
      html: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 24 30"><path fill="#ea4335" stroke="#fff" stroke-width="1" d="M12 0C5.4 0 0 5.4 0 12c0 7.2 12 18 12 18s12-10.8 12-18C24 5.4 18.6 0 12 0z"/><circle fill="#fff" cx="12" cy="10" r="4"/></svg>`,
      iconSize: [32, 40],
      iconAnchor: [16, 40],
      popupAnchor: [0, -40]
    });
    destMarker = L.marker(latlng, { icon: destIcon, pane: "markerPane" }).addTo(map).bindPopup("Destination").openPopup();
  }

  clickMode = null;
  document.body.style.cursor = "default";
  setRouteStatus("");

  if (routeOrigin && routeDestination) calculateRouteSingle();
});

async function handleQuickRoute() {
  const fromKey = document.getElementById("quickRouteFrom")?.value;
  const toKey = document.getElementById("quickRouteTo")?.value;

  if (!fromKey || !toKey) return alert("Please select both From and To.");
  if (fromKey === toKey) return alert("Origin and destination cannot be the same.");

  const fromLoc = PRESET_LOCATIONS[fromKey];
  const toLoc = PRESET_LOCATIONS[toKey];

  clearRoutes();

  routeOrigin = { lat: fromLoc.lat, lng: fromLoc.lon };
  routeDestination = { lat: toLoc.lat, lng: toLoc.lon };

  // Google Maps style pin markers
  const originIcon = L.divIcon({
    className: 'custom-marker',
    html: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 24 30"><path fill="#22c55e" stroke="#fff" stroke-width="1" d="M12 0C5.4 0 0 5.4 0 12c0 7.2 12 18 12 18s12-10.8 12-18C24 5.4 18.6 0 12 0z"/><circle fill="#fff" cx="12" cy="10" r="4"/></svg>`,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40]
  });
  originMarker = L.marker([fromLoc.lat, fromLoc.lon], { icon: originIcon, pane: "markerPane" }).addTo(map).bindPopup(`Origin: ${fromLoc.name}`);

  const destIcon = L.divIcon({
    className: 'custom-marker',
    html: `<svg xmlns="http://www.w3.org/2000/svg" width="32" height="40" viewBox="0 0 24 30"><path fill="#ea4335" stroke="#fff" stroke-width="1" d="M12 0C5.4 0 0 5.4 0 12c0 7.2 12 18 12 18s12-10.8 12-18C24 5.4 18.6 0 12 0z"/><circle fill="#fff" cx="12" cy="10" r="4"/></svg>`,
    iconSize: [32, 40],
    iconAnchor: [16, 40],
    popupAnchor: [0, -40]
  });
  destMarker = L.marker([toLoc.lat, toLoc.lon], { icon: destIcon, pane: "markerPane" }).addTo(map).bindPopup(`Destination: ${toLoc.name}`);

  map.fitBounds(L.latLngBounds([[fromLoc.lat, fromLoc.lon], [toLoc.lat, toLoc.lon]]), { padding: [50, 50] });

  await calculateRouteSingle();
}

/* =========================
   TOGGLES + RESTORE
========================= */
function restoreLayerVisibility() {
  const trafficCheckbox = document.getElementById("toggleTraffic");
  const floodCheckbox = document.getElementById("toggleFlood");
  const trafficPointsCheckbox = document.getElementById("toggleTrafficPoints");

  if (trafficCheckbox?.checked) {
    if (!map.hasLayer(trafficTiles)) map.addLayer(trafficTiles);
    trafficTiles.redraw();
  } else {
    if (map.hasLayer(trafficTiles)) map.removeLayer(trafficTiles);
  }

  if (trafficPointsCheckbox?.checked) {
    trafficPointMarkers.forEach((m) => { if (!map.hasLayer(m)) m.addTo(map); });
  } else {
    trafficPointMarkers.forEach((m) => { if (map.hasLayer(m)) map.removeLayer(m); });
  }

  if (floodCheckbox?.checked) {
    if (floodLayer && !map.hasLayer(floodLayer)) floodLayer.addTo(map);
  } else {
    if (floodLayer && map.hasLayer(floodLayer)) map.removeLayer(floodLayer);
  }
}

map.on("moveend", () => setTimeout(restoreLayerVisibility, 50));

/* =========================
   WIRE UI EVENTS
========================= */
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("searchButton")?.addEventListener("click", handleSearch);
  document.getElementById("refreshTrafficButton")?.addEventListener("click", refreshTraffic);

  document.getElementById("toggleTraffic")?.addEventListener("change", restoreLayerVisibility);
  document.getElementById("toggleTrafficPoints")?.addEventListener("change", restoreLayerVisibility);
  document.getElementById("toggleFlood")?.addEventListener("change", restoreLayerVisibility);

  // Road network overlay toggle
  document.getElementById("toggleRoadNetwork")?.addEventListener("change", (e) => {
    toggleRoadNetwork(e.target.checked);
  });

  document.getElementById("calculateQuickRouteBtn")?.addEventListener("click", handleQuickRoute);
  document.getElementById("clearQuickRoutesBtn")?.addEventListener("click", clearRoutes);

  document.getElementById("setOriginBtn")?.addEventListener("click", setOriginMode);
  document.getElementById("setDestBtn")?.addEventListener("click", setDestinationMode);
  document.getElementById("clearRoutesBtn")?.addEventListener("click", clearRoutes);

  // Flood slider
  const floodSlider = document.getElementById("floodTimeSlider");

  floodSlider?.addEventListener("input", (e) => {
    setFloodTimeLabel(Number(e.target.value));
  });

  floodSlider?.addEventListener("change", async (e) => {
    const idx = Number(e.target.value);

    // Load both flood AND traffic for this timeline index
    await Promise.all([
      loadFloodLayerByIndex(idx),
      loadTrafficSnapshot(idx)  // Sync traffic with flood timeline
    ]);

    // If route already chosen, recalc with this flood time
    if (routeOrigin && routeDestination) await calculateRouteSingle();

    restoreLayerVisibility();
  });

  document.getElementById("reloadFloodButton")?.addEventListener("click", async () => {
    await loadFloodTimeline();
    restoreLayerVisibility();
  });

  // Flood mode change reloads layer
  document.querySelectorAll('input[name="floodMode"]').forEach((el) => {
    el.addEventListener("change", async () => {
      await loadFloodLayerByIndex(currentFloodIndex);
      restoreLayerVisibility();
    });
  });

  // Route checkbox changes -> recalculate routes
  ["routeShortest", "routeTraffic", "routeFlood", "routeSmart"].forEach(id => {
    document.getElementById(id)?.addEventListener("change", async () => {
      if (routeOrigin && routeDestination) await calculateAllRoutes();
    });
  });

  // Panel toggle
  const panelToggle = document.getElementById("panel-toggle");
  const controlPanel = document.getElementById("control-panel");

  panelToggle?.addEventListener("click", () => {
    const isOpen = panelToggle.classList.contains("panel-open");
    if (isOpen) {
      panelToggle.classList.remove("panel-open");
      controlPanel.classList.add("collapsed");
      panelToggle.innerHTML = "☰";
    } else {
      panelToggle.classList.add("panel-open");
      controlPanel.classList.remove("collapsed");
      panelToggle.innerHTML = "✕";
    }
  });

  // Zoom to route
  document.getElementById("zoomToRouteBtn")?.addEventListener("click", () => {
    zoomToRoutes();
  });

  // Init
  loadFloodTimeline();
  loadTrafficSnapshot();
  restoreLayerVisibility();

  // Auto-load road network if checkbox is checked
  if (document.getElementById("toggleRoadNetwork")?.checked) {
    toggleRoadNetwork(true);
  }
});

// Zoom to fit all route layers
function zoomToRoutes() {
  const allBounds = [];

  Object.values(routeLayers).forEach(layer => {
    if (layer) {
      try {
        allBounds.push(layer.getBounds());
      } catch (e) { }
    }
  });

  if (allBounds.length > 0) {
    let combined = allBounds[0];
    for (let i = 1; i < allBounds.length; i++) {
      combined = combined.extend(allBounds[i]);
    }
    map.fitBounds(combined, { padding: [50, 50] });
  } else if (routeOrigin && routeDestination) {
    const bounds = L.latLngBounds([routeOrigin, routeDestination]);
    map.fitBounds(bounds, { padding: [50, 50] });
  }
}

// optional console helpers
window.loadFloodTimeline = loadFloodTimeline;
window.loadFloodLayerByIndex = loadFloodLayerByIndex;
window.calculateRouteSingle = calculateRouteSingle;
window.clearRoutes = clearRoutes;
window.zoomToRoutes = zoomToRoutes;
