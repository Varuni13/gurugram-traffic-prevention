"""
Main server entry point for production deployment.
Uses waitress as WSGI server and imports Flask app from server.api.
Configuration is loaded from the global config module.
"""

import sys
from pathlib import Path

from waitress import serve

# Import global configuration
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Import Flask app
from server.api import app

if __name__ == "__main__":
    host = config.FLASK_HOST
    port = config.FLASK_PORT
    
    print("\n" + "="*70)
    print("[Waitress Server]")
    print("="*70)
    print(f"Starting server on {host}:{port}")
    print(f"CORS Enabled: {config.CORS_ENABLED}")
    print(f"CORS Origins: {config.CORS_ORIGINS}")
    print("="*70 + "\n")
    
    serve(app, host=host, port=port)

