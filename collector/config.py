# collector/config.py

# Put your real TomTom key here (do not commit it to git)
TOMTOM_API_KEY = "SFl0comH2EWPv2QQvZSTdHa8jEiYltGn"

#  10 fixed monitoring points in Gurugram (you can change later)
# Choose major corridors/junction areas for good demo
MONITOR_POINTS = [
    {"name": "IFFCO Chowk", "lat": 28.4726, "lon": 77.0726},
    {"name": "MG Road", "lat": 28.4795, "lon": 77.0806},
    {"name": "Cyber Hub", "lat": 28.4947, "lon": 77.0897},
    {"name": "Golf Course Rd", "lat": 28.4503, "lon": 77.0972},
    {"name": "Sohna Road", "lat": 28.4073, "lon": 77.0460},
    {"name": "NH-48 (Ambience)", "lat": 28.5052, "lon": 77.0970},
    {"name": "Rajiv Chowk", "lat": 28.4691, "lon": 77.0366},
    {"name": "Huda City Centre", "lat": 28.4595, "lon": 77.0722},
    {"name": "Sector 56", "lat": 28.4244, "lon": 77.1070},
    {"name": "Manesar Rd", "lat": 28.3540, "lon": 76.9440},
]
