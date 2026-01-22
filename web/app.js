console.log("APP.JS LOADED:", new Date().toISOString());

/* =========================
   CONFIG
========================= */
const API_BASE = "http://localhost:8000";

// Filter to match traffic data window: 11:25 AM to 6:17 PM (18:17)
// Using July 13, 2025 dates from flood files but matching the time window
const TIMES_URL = `${API_BASE}/api/times?start=2025-07-13T11:25&end=2025-07-13T18:17`;
const FLOOD_POLY_URL = (i) => `${API_BASE}/api/flood?time=${encodeURIComponent(i)}`;
const FLOOD_ROADS_URL = (i) => `${API_BASE}/api/flood-roads?time=${encodeURIComponent(i)}`;
const TRAFFIC_SNAPSHOT_URL = (timeIdx = null) =>
  timeIdx !== null ? `${API_BASE}/api/traffic?time=${encodeURIComponent(timeIdx)}` : `${API_BASE}/api/traffic`;

/* =========================
   TRAFFIC HISTORY FOR CHART
========================= */
const trafficHistory = [];
const MAX_HISTORY_POINTS = 12;
let trafficTrendChart = null;

/* =========================
   DARK MODE TOGGLE
========================= */
function initDarkMode() {
  const savedTheme = localStorage.getItem('theme');
  if (savedTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
    updateDarkModeIcon(true);
  }
}

function toggleDarkMode() {
  const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
  
  if (isDark) {
    document.documentElement.removeAttribute('data-theme');
    localStorage.setItem('theme', 'light');
    updateDarkModeIcon(false);
    showToast('Light mode enabled', 'info', 'Theme Changed');
  } else {
    document.documentElement.setAttribute('data-theme', 'dark');
    localStorage.setItem('theme', 'dark');
    updateDarkModeIcon(true);
    showToast('Dark mode enabled', 'info', 'Theme Changed');
  }
}

function updateDarkModeIcon(isDark) {
  const icon = document.querySelector('.mode-icon');
  if (icon) {
    icon.textContent = isDark ? '☀️' : '🌙';
  }
}

// Initialize dark mode on load
initDarkMode();

/* =========================
   TOAST NOTIFICATIONS
========================= */
let lastAlertTime = 0;
const ALERT_COOLDOWN = 60000; // 1 minute cooldown between alerts

// Track previous traffic state to detect changes
let previousTrafficState = { heavy: null, moderate: null, smooth: null };
let isInitialLoad = true; // Skip alerts on first page load

function showToast(message, type = 'error', title = 'Alert') {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = {
    error: '🚨',
    warning: '⚠️',
    success: '✅',
    info: 'ℹ️'
  };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      <div class="toast-message">${message}</div>
    </div>
    <button class="toast-close" onclick="this.parentElement.remove()">×</button>
  `;
  
  container.appendChild(toast);
  
  // Auto remove after 5 seconds
  setTimeout(() => {
    if (toast.parentElement) {
      toast.remove();
    }
  }, 5000);
}

function checkTrafficAlerts(heavy, moderate, smooth) {
  const now = Date.now();
  
  // Skip alerts on initial page load - just store the state
  if (isInitialLoad) {
    previousTrafficState = { heavy, moderate, smooth };
    isInitialLoad = false;
    console.log('[Alerts] Initial load - storing baseline state:', previousTrafficState);
    return;
  }
  
  // Cooldown to prevent spam
  if (now - lastAlertTime < ALERT_COOLDOWN) return;
  
  const prevHeavy = previousTrafficState.heavy ?? 0;
  const prevModerate = previousTrafficState.moderate ?? 0;
  
  // Check if traffic got WORSE
  const heavyIncreased = heavy > prevHeavy && heavy >= 3;
  const moderateIncreased = moderate > prevModerate && moderate >= 10;
  
  // Check if traffic IMPROVED significantly
  const heavyDecreased = heavy < prevHeavy && prevHeavy >= 3 && heavy <= 1;
  const moderateDecreased = moderate < prevModerate - 5 && prevModerate >= 10;
  
  if (heavyIncreased) {
    const diff = heavy - prevHeavy;
    showToast(
      `Traffic worsened! ${diff} more heavy congestion point${diff > 1 ? 's' : ''} (now ${heavy} total)`,
      'error',
      '🚨 Traffic Alert'
    );
    lastAlertTime = now;
  } else if (moderateIncreased && !heavyIncreased) {
    const diff = moderate - prevModerate;
    showToast(
      `${diff} more locations showing moderate traffic (now ${moderate} total)`,
      'warning', 
      '⚠️ Traffic Advisory'
    );
    lastAlertTime = now;
  } else if (heavyDecreased) {
    showToast(
      `Traffic clearing up! Heavy congestion reduced to ${heavy} point${heavy !== 1 ? 's' : ''}`,
      'success',
      '✅ Traffic Improving'
    );
    lastAlertTime = now;
  }
  
  // Update previous state for next comparison
  previousTrafficState = { heavy, moderate, smooth };
  console.log('[Alerts] Updated traffic state:', previousTrafficState);
}

/* =========================
   TRAFFIC TREND CHART
========================= */
function initTrafficTrendChart() {
  const ctx = document.getElementById('trafficTrendChart');
  if (!ctx || trafficTrendChart) return;

  trafficTrendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: 'Smooth',
          data: [],
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34, 197, 94, 0.2)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 0
        },
        {
          label: 'Moderate',
          data: [],
          borderColor: '#f59e0b',
          backgroundColor: 'rgba(245, 158, 11, 0.2)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 0
        },
        {
          label: 'Heavy',
          data: [],
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.2)',
          borderWidth: 2,
          tension: 0.4,
          fill: true,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
          padding: 8,
          titleFont: { size: 11 },
          bodyFont: { size: 10 }
        }
      },
      scales: {
        x: { display: false },
        y: { display: false, beginAtZero: true }
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false
      }
    }
  });
  
  console.log("[Chart] Traffic trend chart initialized");
}

function updateTrafficTrendChart(smooth, moderate, heavy) {
  if (!trafficTrendChart) {
    initTrafficTrendChart();
    if (!trafficTrendChart) return;
  }

  const now = new Date();
  const timeLabel = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

  // Add new data point
  trafficHistory.push({ time: timeLabel, smooth, moderate, heavy });
  
  // Keep only last N points
  if (trafficHistory.length > MAX_HISTORY_POINTS) {
    trafficHistory.shift();
  }

  // Update chart
  trafficTrendChart.data.labels = trafficHistory.map(h => h.time);
  trafficTrendChart.data.datasets[0].data = trafficHistory.map(h => h.smooth);
  trafficTrendChart.data.datasets[1].data = trafficHistory.map(h => h.moderate);
  trafficTrendChart.data.datasets[2].data = trafficHistory.map(h => h.heavy);
  
  trafficTrendChart.update('none');
}

/* =========================
   TRAFFIC STATUS COUNTS - For Header Cards
========================= */
function updateTrafficStatusCounts(points) {
  let smooth = 0, moderate = 0, heavy = 0;
  
  if (points && Array.isArray(points)) {
    points.forEach(p => {
      const sr = Number(p.speed_ratio ?? 0);
      if (sr >= 0.85) smooth++;
      else if (sr >= 0.65) moderate++;
      else heavy++;
    });
  }
  
  // Update the status cards
  const smoothEl = document.getElementById("smoothCount");
  const moderateEl = document.getElementById("moderateCount");
  const heavyEl = document.getElementById("heavyCount");
  
  if (smoothEl) smoothEl.textContent = smooth;
  if (moderateEl) moderateEl.textContent = moderate;
  if (heavyEl) heavyEl.textContent = heavy;
  
  // ★ Update traffic trend chart
  updateTrafficTrendChart(smooth, moderate, heavy);
  
  // ★ Check for alerts (pass all three counts)
  checkTrafficAlerts(heavy, moderate, smooth);
  
  console.log(`[Traffic Status] Smooth: ${smooth}, Moderate: ${moderate}, Heavy: ${heavy}`);
}

/* =========================
   ZOOM TO TRAFFIC POINTS BY CATEGORY
========================= */
function zoomToTrafficPoints(category) {
  const markers = trafficPointMarkers[category];
  
  if (!markers || markers.length === 0) {
    console.log(`[Zoom] No ${category} traffic points to zoom to`);
    return;
  }
  
  // Create bounds from all markers of this category
  const bounds = L.latLngBounds();
  markers.forEach(marker => {
    bounds.extend(marker.getLatLng());
  });
  
  // Fit map to bounds with padding
  map.fitBounds(bounds, { 
    padding: [50, 50],
    maxZoom: 16
  });
  
  // Flash the markers to highlight them
  markers.forEach(marker => {
    const originalRadius = marker.options.radius;
    const originalWeight = marker.options.weight;
    
    // Pulse effect
    marker.setStyle({ radius: originalRadius * 1.8, weight: 4 });
    setTimeout(() => {
      marker.setStyle({ radius: originalRadius * 1.5, weight: 3 });
    }, 150);
    setTimeout(() => {
      marker.setStyle({ radius: originalRadius, weight: originalWeight });
    }, 300);
  });
  
  console.log(`[Zoom] Zoomed to ${markers.length} ${category} traffic points`);
}

// Initialize status card click handlers
function initStatusCardClickHandlers() {
  const cards = {
    'status-smooth': 'smooth',
    'status-moderate': 'moderate', 
    'status-heavy': 'heavy'
  };
  
  Object.entries(cards).forEach(([className, category]) => {
    const card = document.querySelector(`.${className}`);
    if (card) {
      card.style.cursor = 'pointer';
      card.title = `Click to zoom to ${category} traffic points`;
      card.addEventListener('click', () => zoomToTrafficPoints(category));
    }
  });
  
  console.log('[Init] Status card click handlers initialized');
}

/* =========================
   HEADER TIME UPDATE
========================= */
function updateHeaderTime() {
  const el = document.getElementById("headerTime");
  if (el) {
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-IN', { 
      hour: '2-digit', 
      minute: '2-digit',
      hour12: true 
    });
  }
}

// Update header time every minute
setInterval(updateHeaderTime, 60000);
updateHeaderTime(); // Initial call

// Wire up dark mode toggle
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('darkModeToggle')?.addEventListener('click', toggleDarkMode);
  
  // Initialize chart after short delay
  setTimeout(initTrafficTrendChart, 1000);
  
  // Initialize status card click handlers
  initStatusCardClickHandlers();
});

// 25 Traffic Hotspots for Gurugram
const PRESET_LOCATIONS = {
  iffco_chowk: { name: "IFFCO Chowk", lat: 28.477564199478913, lon: 77.06859985177209 },
  rajiv_chowk: { name: "Rajiv Chowk", lat: 28.445292087715444, lon: 77.03318302971367 },
  hero_honda: { name: "Hero Honda Chowk", lat: 28.429572485292674, lon: 77.02009547931516 },
  kherki_daula: { name: "Kherki Daula Toll Plaza", lat: 28.395715221700556, lon: 76.98214491369943 },
  signature_tower: { name: "Signature Tower", lat: 28.462211223747214, lon: 77.0489446912307 },
  shankar_chowk: { name: "Shankar Chowk / Cyber City", lat: 28.508064947117724, lon: 77.08211742534732 },
  sikanderpur: { name: "Sikanderpur Metro", lat: 28.481187691171193, lon: 77.09425732449982 },
  huda_city: { name: "HUDA City Centre Metro", lat: 28.459382783815194, lon: 77.07285799465937 },
  subhash_chowk: { name: "Subhash Chowk", lat: 28.428861106525773, lon: 77.03711785417951 },
  jharsa_chowk: { name: "Jharsa Chowk", lat: 28.454834178543077, lon: 77.04244784380403 },
  atul_kataria: { name: "Atul Kataria Chowk", lat: 28.481183722468575, lon: 77.04867463883903 },
  mahavir_chowk: { name: "Mahavir Chowk", lat: 28.463656522868447, lon: 77.03413268301684 },
  ghata_chowk: { name: "Ghata Chowk", lat: 28.421982117566415, lon: 77.10973463698622 },
  vatika_chowk: { name: "Vatika Chowk (SPR-Sohna Rd)", lat: 28.404865793781532, lon: 77.04204962349263 },
  badshahpur: { name: "Badshahpur / Sohna Rd junction", lat: 28.35048237859808, lon: 77.0655043369831 },
  ambedkar_chowk: { name: "Ambedkar Chowk", lat: 28.437148333410683, lon: 77.0674060560299 },
  dundahera: { name: "Dundahera Hanuman Mandir (Old Delhi Rd)", lat: 28.511407097088824, lon: 77.07777883884035 },
  dwarka_nh48: { name: "Dwarka Expwy-NH48 Cloverleaf", lat: 28.40601139485718, lon: 76.9902767658213 },
  sector31: { name: "Sector 31 Signal / Market", lat: 28.456542851852696, lon: 77.04977988988432 },
  old_bus_stand: { name: "Old Gurgaon Bus Stand", lat: 28.466952871185878, lon: 77.03269036613194 },
  imt_manesar: { name: "IMT Manesar Junction", lat: 28.360673595292468, lon: 76.93919787004663 },
  golf_course: { name: "Golf Course Rd - One Horizon", lat: 28.4513013391806, lon: 77.09741156582324 },
  sector56_57: { name: "Sector 56/57 - Golf Course Extn", lat: 28.448653219922612, lon: 77.09931976915546 },
  sohna_entry: { name: "Sohna Town Entry", lat: 28.419803693042986, lon: 77.04230448203113 },
  pataudi_rd: { name: "Pataudi Rd - Sector 89/90", lat: 28.427631686155653, lon: 76.94592366161731 }
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
const map = L.map("map", { zoomControl: true, maxZoom: 18 }).setView([28.4595, 77.0266], 13);

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

// Store all base layers for selector
const baseLayers = {
  googleStreets,
  googleSatellite,
  googleHybrid,
  googleTerrain,
  osmStandard,
  baseLight,
  baseDark,
  satellite
};

let currentBaseLayer = googleStreets;

// Base map selector handler
function initBaseMapSelector() {
  const selector = document.getElementById('baseMapSelector');
  if (!selector) return;
  
  selector.addEventListener('change', (e) => {
    const layerName = e.target.value;
    const newLayer = baseLayers[layerName];
    
    if (newLayer && newLayer !== currentBaseLayer) {
      map.removeLayer(currentBaseLayer);
      newLayer.addTo(map);
      currentBaseLayer = newLayer;
      
      // Save preference
      localStorage.setItem('preferredBaseMap', layerName);
    }
  });
  
  // Restore saved preference
  const saved = localStorage.getItem('preferredBaseMap');
  if (saved && baseLayers[saved]) {
    selector.value = saved;
    if (baseLayers[saved] !== currentBaseLayer) {
      map.removeLayer(currentBaseLayer);
      baseLayers[saved].addTo(map);
      currentBaseLayer = baseLayers[saved];
    }
  }
}

// Hide the default Leaflet layer control (we use our own dropdown now)
// L.control.layers not added

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
  const elScenario = document.getElementById("scenarioFloodTime"); // Old panel label (removed from HTML but kept for safety)
  const elSliderTime = document.getElementById("sliderCurrentTime"); // New slider time label

  const item = floodTimes.find((x) => Number(x.index) === Number(idx));
  // Simplified: Just show time for end users
  const text = item && item.label ? item.label.split(" ")[1] || item.label : `Time ${idx}`;

  if (el) el.textContent = text;

  // Update New Slider Time Display
  if (elSliderTime) {
    if (item && item.label) {
      elSliderTime.textContent = formatLabel(item.label, window.floodTimelineSpansDays);
    } else {
      elSliderTime.textContent = text;
    }
  }

  // Update Scenario Panel (if it still existed)
  if (elScenario) {
    elScenario.textContent = elSliderTime ? elSliderTime.textContent : text;
  }
}

async function loadFloodTimeline() {
  try {
    setFloodTimelineStatus("Flood timeline: loading…");
    console.log("[Flood Timeline] Fetching from:", TIMES_URL);

    const res = await fetch(TIMES_URL, { cache: "no-store" });
    console.log("[Flood Timeline] Response status:", res.status, res.statusText);

    const data = await res.json();
    console.log("[Flood Timeline] Response data:", data);

    if (!res.ok) {
      throw new Error(data?.error || `Times fetch failed: ${res.status}`);
    }

    floodTimes = Array.isArray(data.files) ? data.files : [];

    if (floodTimes.length === 0) {
      currentFloodIndex = 0;
      setFloodTimelineStatus("Flood timeline: no snapshots found");
      setFloodTimeLabel(0);
      return;
    }

    const indices = floodTimes.map((x) => Number(x.index)).filter(Number.isFinite);
    const minIdx = Math.min(...indices);
    const maxIdx = Math.max(...indices);

    currentFloodIndex = minIdx;
    setFloodTimeLabel(currentFloodIndex);

    // Configure slider
    const slider = document.getElementById("floodTimeSlider");
    if (slider) {
      slider.min = String(minIdx);
      slider.max = String(maxIdx);
      slider.value = String(minIdx);
    }

    // Show time range info on slider labels
    const firstTime = floodTimes[0]?.label || "";
    const lastTime = floodTimes[floodTimes.length - 1]?.label || "";
    const startLabel = document.getElementById("sliderStartTime");
    const endLabel = document.getElementById("sliderEndTime");

    // Check if dates are different
    let showDate = false;
    if (firstTime && lastTime) {
      const d1 = firstTime.split(" ")[0]; // YYYY-MM-DD
      const d2 = lastTime.split(" ")[0];
      if (d1 !== d2) showDate = true;
    }

    // Expose this for setFloodTimeLabel to use
    window.floodTimelineSpansDays = showDate;

    if (startLabel && firstTime) {
      // If spanning days, show "Jul 13 01:55", else "01:55"
      startLabel.textContent = formatLabel(firstTime, showDate);
    }
    if (endLabel && lastTime) {
      endLabel.textContent = formatLabel(lastTime, showDate);
    }

    // Simplified status for end users
    setFloodTimelineStatus("✓ Data Ready");

    await loadFloodLayerByIndex(currentFloodIndex);
  } catch (err) {
    console.error("=== FLOOD TIMELINE ERROR ===");
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);
    console.error("Full error object:", err);
    console.error("Stack trace:", err.stack);
    console.error("URL attempted:", TIMES_URL);
    console.error("=============================");
    setFloodTimelineStatus("Flood timeline: failed to load (check console /api/times)");
  }
}

function formatLabel(fullLabel, showDate) {
  if (!fullLabel) return "--:--";
  if (!showDate) {
    // Just time: "12:30"
    return fullLabel.split(" ")[1] || fullLabel;
  }
  // Date + Time: "2025-07-13 12:30" -> "Jul 13, 12:30"
  try {
    const d = new Date(fullLabel.replace(" ", "T"));
    const month = d.toLocaleString('en-US', { month: 'short' });
    const day = d.getDate();
    const time = fullLabel.split(" ")[1];
    return `${month} ${day}, ${time}`;
  } catch (e) {
    return fullLabel;
  }
}

// In-memory cache for flood layers (key: "mode_index", value: geojson)
const floodDataCache = {};

async function loadFloodLayerByIndex(idx) {
  try {
    currentFloodIndex = Number(idx);
    setFloodTimeLabel(currentFloodIndex);

    const mode = getFloodMode();
    const cacheKey = `${mode}_${currentFloodIndex}`;

    let geojson;

    // Check in-memory cache first
    if (floodDataCache[cacheKey]) {
      console.log(`[Flood] Using cached data for index ${currentFloodIndex}`);
      geojson = floodDataCache[cacheKey];
    } else {
      const url = mode === "polygons" ? FLOOD_POLY_URL(currentFloodIndex) : FLOOD_ROADS_URL(currentFloodIndex);
      const res = await fetch(url);  // Allow browser caching (removed no-store)
      geojson = await res.json();

      if (!res.ok) throw new Error(geojson?.error || `Flood fetch failed: ${res.status}`);
      if (geojson?.error) throw new Error(geojson.error);

      // Store in cache
      floodDataCache[cacheKey] = geojson;
      console.log(`[Flood] Cached data for index ${currentFloodIndex}`);
    }

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

      // Light sky blue for flooded roads (distinct from route blue)
      style: {
        color: "#38BDF8",  // Light sky blue (Tailwind sky-400)
        weight: 4,
        opacity: 0.9
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
      // Extract just TIME from traffic timestamp
      const trafficTimeOnly = data.traffic_time_ist.split(" ")[1] || data.traffic_time_ist.split("T")[1]?.substring(0, 5) || data.traffic_time_ist;
      // Show time only - we match by time of day, not date
      el.textContent = trafficTimeOnly;
      el.style.color = "#166534";
    } else {
      el.textContent = "No match";
      el.style.color = "#f59e0b";  // amber
    }
  } catch (err) {
    el.textContent = "Unavailable";
    el.style.color = "#dc2626";  // red
  }
}

/* =========================
   TRAFFIC SNAPSHOT POINTS
========================= */
let trafficSnapshot = null;
let trafficPointMarkers = {
  smooth: [],
  moderate: [],
  heavy: [],
  all: [] // Keep a flat list for backward compatibility
};

function clearTrafficPointMarkers() {
  trafficPointMarkers.all.forEach((m) => map.removeLayer(m));
  trafficPointMarkers = { smooth: [], moderate: [], heavy: [], all: [] };
}

async function loadTrafficSnapshot(timeIdx = null) {
  const statusEl = document.getElementById("snapshotStatus");
  try {
    if (statusEl) statusEl.textContent = "Traffic snapshot: loading...";
    const url = TRAFFIC_SNAPSHOT_URL(timeIdx);
    console.log("[Traffic Snapshot] Fetching from:", url);

    const res = await fetch(url, { cache: "no-store" });
    console.log("[Traffic Snapshot] Response status:", res.status, res.statusText);

    const data = await res.json();
    console.log("[Traffic Snapshot] Response data:", data);

    if (!res.ok) throw new Error(data?.error || `Traffic snapshot fetch failed: ${res.status}`);

    trafficSnapshot = data;
    clearTrafficPointMarkers();

    const points = trafficSnapshot.points || [];
    const updated = trafficSnapshot.generated_at_local || formatTimeNice(trafficSnapshot.generated_at_utc);

    // ★ UPDATE TRAFFIC STATUS CARDS IN HEADER
    updateTrafficStatusCounts(points);

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
      
      // Categorize marker by speed ratio
      const category = sr >= 0.85 ? 'smooth' : sr >= 0.65 ? 'moderate' : 'heavy';
      trafficPointMarkers[category].push(marker);
      trafficPointMarkers.all.push(marker);
    });

    console.log("✓ Traffic snapshot markers loaded:", trafficPointMarkers.all.length, timeIdx !== null ? `(synced to index ${timeIdx})` : "");
  } catch (err) {
    console.error("=== TRAFFIC SNAPSHOT ERROR ===");
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);
    console.error("Full error object:", err);
    console.error("Stack trace:", err.stack);
    console.error("URL attempted:", TRAFFIC_SNAPSHOT_URL(timeIdx));
    console.error("=============================");
    if (statusEl) statusEl.textContent = "Traffic snapshot: failed to load";
  }
}

async function refreshTraffic() {
  const statusEl = document.getElementById("snapshotStatus");
  try {
    if (statusEl) statusEl.textContent = "Refreshing traffic...";
    const refreshUrl = `${API_BASE}/api/traffic/refresh`;
    console.log("[Refresh Traffic] Fetching from:", refreshUrl);

    await fetch(refreshUrl, { method: "POST" }).catch((err) => {
      console.error("[Refresh Traffic] POST request failed:", err);
    });
    await loadTrafficSnapshot();
  } catch (err) {
    console.error("=== REFRESH TRAFFIC ERROR ===");
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);
    console.error("Full error object:", err);
    console.error("Stack trace:", err.stack);
    console.error("=============================");
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
    const url = `${API_BASE}/api/tomtom/geocode?search=${encodeURIComponent(searchTerm)}`;
    console.log("[Search] Fetching from:", url);

    const res = await fetch(url);
    console.log("[Search] Response status:", res.status, res.statusText);

    const data = await res.json();
    console.log("[Search] Response data:", data);

    if (!res.ok) throw new Error(data?.error || "Failed to fetch geocode data");

    if (!data.results?.length) return alert("Location not found.");

    const { lat, lon } = data.results[0].position;

    if (searchMarker) map.removeLayer(searchMarker);
    searchMarker = L.marker([lat, lon]).addTo(map).bindPopup(searchTerm).openPopup();
    map.setView([lat, lon], 14);

    setTimeout(restoreLayerVisibility, 150);
  } catch (err) {
    console.error("=== SEARCH ERROR ===");
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);
    console.error("Full error object:", err);
    console.error("Stack trace:", err.stack);
    console.error("Search term:", searchTerm);
    console.error("====================");
    alert("Error searching location.");
  }
}

/* =========================
   ROUTING - Multi-route comparison
========================= */
// Route colors - avoiding traffic colors (green/red/orange in traffic)
const ROUTE_COLORS = {
  shortest: "#673AB7",    // Purple
  fastest: "#E91E63",     // Pink/Magenta
  flood_avoid: "#1B5E20", // Dark Green
  smart: "#000000"        // Black
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
  const el = document.getElementById("routeSearchStatus");
  if (el) {
    el.textContent = msg || "";
    // Reset color if clearing
    if (!msg) el.style.color = "";
    // If success message (starts with ✅), make it green/blue
    if (msg && msg.startsWith("✅")) el.style.color = "#10b981";
  }
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
    console.log(`[Route ${routeType}] Fetching from:`, url);
    const res = await fetch(url);
    console.log(`[Route ${routeType}] Response status:`, res.status, res.statusText);

    const geojson = await res.json();
    console.log(`[Route ${routeType}] Response data:`, geojson);

    if (!res.ok || geojson?.error) {
      console.warn(`Route ${routeType} failed:`, geojson?.error || res.status);
      return null;
    }
    return { routeType, geojson };
  } catch (err) {
    console.error(`=== ROUTE ${routeType.toUpperCase()} ERROR ===`);
    console.error("Error name:", err.name);
    console.error("Error message:", err.message);
    console.error("Full error object:", err);
    console.error("Stack trace:", err.stack);
    console.error("URL attempted:", url);
    console.error("=============================");
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
    setRouteStatus(`✅ ${successCount} route(s) ready`);
    setTimeout(() => setRouteStatus(""), 1500);  // Hide quickly
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
  tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#94a3b8;">Calculating...</td></tr>';

  // Route colors matching the map lines
  const types = [
    { id: "shortest", label: "Shortest", color: "#673AB7" },
    { id: "fastest", label: "Fastest", color: "#E91E63" },
    { id: "flood_avoid", label: "Flood-Avoid", color: "#1B5E20" },
    { id: "smart", label: "Smart", color: "#000000" }
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

    // Find the best (fastest) ETA among successful results
    let bestEta = Infinity;
    results.forEach(res => {
      if (res.success && res.data.properties) {
        const eta = res.data.properties.eta_s;
        if (eta < bestEta) bestEta = eta;
      }
    });

    results.forEach(res => {
      const type = res.type;
      const tr = document.createElement("tr");

      if (!res.success) {
        tr.innerHTML = `
            <td><span class="route-color-dot" style="background:${type.color}"></span>${type.label}</td>
            <td colspan="2" class="route-failed">Unavailable</td>
         `;
        tbody.appendChild(tr);
        return;
      }

      const props = res.data.properties;
      const etaMin = Math.round(props.eta_s / 60);
      const distKm = (props.distance_m / 1000).toFixed(1);
      const isBest = props.eta_s === bestEta;

      // Highlight best route row
      if (isBest) {
        tr.classList.add("best-route");
      }

      tr.innerHTML = `
        <td><span class="route-color-dot" style="background:${type.color}"></span>${type.label}</td>
        <td>${distKm} km</td>
        <td class="eta-cell">${etaMin} min${isBest ? '<span class="best-badge">Fastest</span>' : ''}</td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Comparison fatal error:", err);
    tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; color:#ef4444;">Error loading routes</td></tr>';
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
    const idx = Number(e.target.value);
    setFloodTimeLabel(idx);
    // Also update traffic sync info while dragging slider
    updateTrafficSyncInfo(idx);
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

  // ★ TIME STEP BUTTONS (Prev/Next)
  const timePrevBtn = document.getElementById("timePrevBtn");
  const timeNextBtn = document.getElementById("timeNextBtn");

  async function stepSlider(direction) {
    const slider = document.getElementById("floodTimeSlider");
    if (!slider) return;

    const min = Number(slider.min);
    const max = Number(slider.max);
    const current = Number(slider.value);
    const newValue = direction === "prev" 
      ? Math.max(min, current - 1) 
      : Math.min(max, current + 1);

    if (newValue !== current) {
      slider.value = newValue;
      setFloodTimeLabel(newValue);
      await Promise.all([
        loadFloodLayerByIndex(newValue),
        loadTrafficSnapshot(newValue)
      ]);
      if (routeOrigin && routeDestination) await calculateRouteSingle();
      restoreLayerVisibility();
    }
  }

  timePrevBtn?.addEventListener("click", () => stepSlider("prev"));
  timeNextBtn?.addEventListener("click", () => stepSlider("next"));

  // ★ QUICK JUMP BUTTONS (Start/Middle/End)
  document.querySelectorAll(".time-quick-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const slider = document.getElementById("floodTimeSlider");
      if (!slider) return;

      const min = Number(slider.min);
      const max = Number(slider.max);
      const jumpTo = btn.dataset.jump;

      let newValue;
      if (jumpTo === "start") newValue = min;
      else if (jumpTo === "end") newValue = max;
      else newValue = Math.round((min + max) / 2); // middle

      slider.value = newValue;
      setFloodTimeLabel(newValue);
      await Promise.all([
        loadFloodLayerByIndex(newValue),
        loadTrafficSnapshot(newValue)
      ]);
      if (routeOrigin && routeDestination) await calculateRouteSingle();
      restoreLayerVisibility();
    });
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
  initBaseMapSelector();  // Initialize base map dropdown
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

/* =========================
   ACCORDION TOGGLE
========================= */
function toggleAccordion(sectionId) {
  const content = document.getElementById(sectionId);
  const chevron = document.getElementById(`${sectionId}-chevron`);

  if (!content || !chevron) return;

  const isCollapsed = content.classList.contains('collapsed');

  if (isCollapsed) {
    // Expand
    content.classList.remove('collapsed');
    chevron.textContent = '▼';
    chevron.style.transform = 'rotate(0deg)';
  } else {
    // Collapse
    content.classList.add('collapsed');
    chevron.textContent = '▶';
    chevron.style.transform = 'rotate(-90deg)';
  }
}

// Make it globally accessible
window.toggleAccordion = toggleAccordion;
window.zoomToRoutes = zoomToRoutes;

/* =========================
   INITIALIZATION - Load data when page loads
========================= */
console.log("[Init] Initializing dashboard...");

// Load flood timeline immediately (includes setting times)
loadFloodTimeline().then(() => {
  console.log("[Init] Flood timeline loaded");

  // Set up slider event listener after timeline is loaded
  const slider = document.getElementById("floodTimeSlider");
  if (slider) {
    slider.addEventListener("input", (e) => {
      const newIndex = Number(e.target.value);
      setFloodTimeLabel(newIndex);
      loadFloodLayerByIndex(newIndex);
    });
    console.log("[Init] Slider event listener attached");
  }
}).catch(err => {
  console.error("[Init] Failed to load flood timeline:", err);
});

// Load traffic snapshot immediately
loadTrafficSnapshot().then(() => {
  console.log("[Init] Traffic snapshot loaded");
}).catch(err => {
  console.error("[Init] Failed to load traffic snapshot:", err);
});

console.log("[Init] Dashboard ready - map should be visible");

/* =========================
   GOOGLE MAPS STYLE DUAL SEARCH
========================= */
let originSearchTimeout = null;
let destSearchTimeout = null;
let searchOriginResult = null;
let searchDestResult = null;

const originSearchInput = document.getElementById("originSearchInput");
const destSearchInput = document.getElementById("destSearchInput");
const originSearchResults = document.getElementById("originSearchResults");
const destSearchResults = document.getElementById("destSearchResults");
const findRoutesBtn = document.getElementById("findRoutesBtn");
const swapLocationsBtn = document.getElementById("swapLocationsBtn");
const routeSearchStatus = document.getElementById("routeSearchStatus");

// Nominatim API search (reusable) - RESTRICTED TO GURUGRAM
async function performNominatimSearch(query, resultsContainer, onSelect) {
  try {
    // Expanded Gurugram bounds (covers entire Gurugram district)
    // Format: left,bottom,right,top (min_lon, min_lat, max_lon, max_lat)
    const viewbox = "76.82,28.35,77.18,28.58";
    
    // bounded=1 strictly limits results to within the viewbox
    const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query + ", Gurugram")}&viewbox=${viewbox}&bounded=1&limit=6&countrycodes=in`;

    const response = await fetch(url, {
      headers: { "User-Agent": "Gurugram-Traffic-Dashboard/1.0" }
    });

    if (!response.ok) throw new Error("Search failed");
    const results = await response.json();

    if (!results || results.length === 0) {
      resultsContainer.innerHTML = '<div class="search-no-results">📍 No locations found in Gurugram area</div>';
      return;
    }

    resultsContainer.innerHTML = results.map((r, i) => {
      const name = r.display_name.split(",")[0];
      const address = r.display_name.split(",").slice(1, 3).join(",");
      return `
        <div class="search-result-item" data-lat="${r.lat}" data-lon="${r.lon}" data-name="${name}">
          <div class="search-result-name">${name}</div>
          <div class="search-result-address">${address}</div>
        </div>
      `;
    }).join("");

    resultsContainer.querySelectorAll(".search-result-item").forEach(item => {
      item.addEventListener("click", () => onSelect(item, resultsContainer));
    });
  } catch (err) {
    console.error("[Search] Error:", err);
    resultsContainer.innerHTML = '<div class="search-no-results">Search failed</div>';
  }
}

// Debounced search for origin
function debounceOriginSearch(query) {
  if (originSearchTimeout) clearTimeout(originSearchTimeout);
  if (!query || query.length < 3) {
    originSearchResults.style.display = "none";
    return;
  }
  originSearchResults.innerHTML = '<div class="search-loading">🔍 Searching...</div>';
  originSearchResults.style.display = "block";
  originSearchTimeout = setTimeout(() => {
    performNominatimSearch(query, originSearchResults, selectOriginResult);
  }, 400);
}

// Debounced search for destination
function debounceDestSearch(query) {
  if (destSearchTimeout) clearTimeout(destSearchTimeout);
  if (!query || query.length < 3) {
    destSearchResults.style.display = "none";
    return;
  }
  destSearchResults.innerHTML = '<div class="search-loading">🔍 Searching...</div>';
  destSearchResults.style.display = "block";
  destSearchTimeout = setTimeout(() => {
    performNominatimSearch(query, destSearchResults, selectDestResult);
  }, 400);
}

// Select origin result
function selectOriginResult(item, container) {
  const lat = parseFloat(item.dataset.lat);
  const lon = parseFloat(item.dataset.lon);
  const name = item.dataset.name;

  searchOriginResult = { lat, lon, name };
  originSearchInput.value = name;
  originSearchInput.classList.add("has-value");
  container.style.display = "none";

  // Update origin marker - use routeOrigin for routing!
  routeOrigin = { lat, lng: lon };
  if (originMarker) map.removeLayer(originMarker);
  originMarker = L.marker([lat, lon], {
    icon: L.divIcon({
      className: "custom-marker",
      html: '<div class="marker-pin marker-origin-pin"><span>A</span></div>',
      iconSize: [30, 40],
      iconAnchor: [15, 40]
    }),
    pane: "markerPane"
  }).addTo(map);

  document.getElementById("originLabel").textContent = name;
  updateRouteStatus();
  console.log(`[Search] Origin: ${name}`);
}

// Select destination result
function selectDestResult(item, container) {
  const lat = parseFloat(item.dataset.lat);
  const lon = parseFloat(item.dataset.lon);
  const name = item.dataset.name;

  searchDestResult = { lat, lon, name };
  destSearchInput.value = name;
  destSearchInput.classList.add("has-value");
  container.style.display = "none";

  // Update destination marker - use routeDestination for routing!
  routeDestination = { lat, lng: lon };
  if (destMarker) map.removeLayer(destMarker);
  destMarker = L.marker([lat, lon], {
    icon: L.divIcon({
      className: "custom-marker",
      html: '<div class="marker-pin marker-dest-pin"><span>B</span></div>',
      iconSize: [30, 40],
      iconAnchor: [15, 40]
    }),
    pane: "markerPane"
  }).addTo(map);

  document.getElementById("destLabel").textContent = name;
  updateRouteStatus();
  console.log(`[Search] Destination: ${name}`);
}

// Update status message
function updateRouteStatus() {
  if (routeSearchStatus) {
    if (searchOriginResult && searchDestResult) {
      routeSearchStatus.textContent = "✅ Ready to find routes!";
      routeSearchStatus.style.color = "#16a34a";
    } else if (searchOriginResult) {
      routeSearchStatus.textContent = "Enter destination...";
      routeSearchStatus.style.color = "#64748b";
    } else if (searchDestResult) {
      routeSearchStatus.textContent = "Enter origin...";
      routeSearchStatus.style.color = "#64748b";
    } else {
      routeSearchStatus.textContent = "";
    }
  }
}

// Swap origin and destination
if (swapLocationsBtn) {
  swapLocationsBtn.addEventListener("click", () => {
    // Swap data
    const tempResult = searchOriginResult;
    searchOriginResult = searchDestResult;
    searchDestResult = tempResult;

    const tempLatLng = routeOrigin;
    routeOrigin = routeDestination;
    routeDestination = tempLatLng;

    // Swap input values
    const tempValue = originSearchInput.value;
    originSearchInput.value = destSearchInput.value;
    destSearchInput.value = tempValue;

    // Update markers
    if (routeOrigin && routeDestination) {
      if (originMarker) map.removeLayer(originMarker);
      if (destMarker) map.removeLayer(destMarker);

      originMarker = L.marker([routeOrigin.lat, routeOrigin.lng], {
        icon: L.divIcon({
          className: "custom-marker",
          html: '<div class="marker-pin marker-origin-pin"><span>A</span></div>',
          iconSize: [30, 40], iconAnchor: [15, 40]
        }), pane: "markerPane"
      }).addTo(map);

      destMarker = L.marker([routeDestination.lat, routeDestination.lng], {
        icon: L.divIcon({
          className: "custom-marker",
          html: '<div class="marker-pin marker-dest-pin"><span>B</span></div>',
          iconSize: [30, 40], iconAnchor: [15, 40]
        }), pane: "markerPane"
      }).addTo(map);
    }

    console.log("[Search] Swapped origin and destination");
  });
}

// Find Routes button
if (findRoutesBtn) {
  findRoutesBtn.addEventListener("click", () => {
    // Check if user typed but didn't select from dropdown
    const originText = originSearchInput?.value.trim();
    const destText = destSearchInput?.value.trim();

    if (!routeOrigin && originText) {
      routeSearchStatus.textContent = "⚠️ Select origin from dropdown";
      routeSearchStatus.style.color = "#dc2626";
      return;
    }
    if (!routeDestination && destText) {
      routeSearchStatus.textContent = "⚠️ Select destination from dropdown";
      routeSearchStatus.style.color = "#dc2626";
      return;
    }
    if (!routeOrigin || !routeDestination) {
      routeSearchStatus.textContent = "⚠️ Please enter both origin and destination";
      routeSearchStatus.style.color = "#dc2626";
      return;
    }

    // Zoom to fit both points
    const bounds = L.latLngBounds([
      [routeOrigin.lat, routeOrigin.lng],
      [routeDestination.lat, routeDestination.lng]
    ]);
    map.fitBounds(bounds, { padding: [50, 50] });

    // Calculate routes
    calculateAllRoutes();
    routeSearchStatus.textContent = "🔄 Calculating routes...";
    routeSearchStatus.style.color = "#3b82f6";
  });
}

// Event listeners for inputs
if (originSearchInput) {
  originSearchInput.addEventListener("input", (e) => debounceOriginSearch(e.target.value.trim()));
  originSearchInput.addEventListener("focus", () => {
    if (originSearchInput.value.length >= 3) originSearchResults.style.display = "block";
  });
}

if (destSearchInput) {
  destSearchInput.addEventListener("input", (e) => debounceDestSearch(e.target.value.trim()));
  destSearchInput.addEventListener("focus", () => {
    if (destSearchInput.value.length >= 3) destSearchResults.style.display = "block";
  });
}

// Hide dropdowns when clicking outside
document.addEventListener("click", (e) => {
  if (!e.target.closest("#originSearchInput") && !e.target.closest("#originSearchResults")) {
    originSearchResults.style.display = "none";
  }
  if (!e.target.closest("#destSearchInput") && !e.target.closest("#destSearchResults")) {
    destSearchResults.style.display = "none";
  }
});

console.log("[Init] Dual search initialized");
