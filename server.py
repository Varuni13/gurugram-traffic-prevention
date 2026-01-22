"""
Main server entry point for production deployment.
Uses waitress as WSGI server and imports Flask app from server.api.
Configuration is loaded from the global config module.

This entry point now also starts the traffic data collector scheduler
as a background thread so both the server and scheduler run together.
"""

import sys
import threading
import time
from pathlib import Path

from waitress import serve

# Import global configuration
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config

# Import Flask app
from server.api import app

# ============================================================================
# SCHEDULER MANAGEMENT (runs in a background thread)
# ============================================================================

scheduler_thread = None
scheduler_running = False

def run_scheduler_in_thread():
    """Import and run the scheduler directly in a thread."""
    global scheduler_running
    
    try:
        # Add collector to path and import the scheduler functions
        collector_path = Path(__file__).resolve().parent / "collector"
        sys.path.insert(0, str(collector_path))
        
        from run_scheduler import run_scheduler
        
        print("✅ Traffic scheduler thread started")
        scheduler_running = True
        
        # Run the scheduler (this blocks until stopped)
        run_scheduler()
        
    except Exception as e:
        print(f"❌ Scheduler error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scheduler_running = False


def start_scheduler_background():
    """Start the traffic data collector scheduler in a background thread."""
    global scheduler_thread
    
    try:
        scheduler_thread = threading.Thread(
            target=run_scheduler_in_thread,
            name="TrafficScheduler",
            daemon=True  # Daemon thread will stop when main program exits
        )
        scheduler_thread.start()
        
        # Give it a moment to start
        time.sleep(1)
        
        if scheduler_thread.is_alive():
            print(f"📊 Scheduler running in background thread")
        else:
            print("❌ Scheduler thread failed to start")
        
    except Exception as e:
        print(f"❌ Failed to start scheduler: {e}")


if __name__ == "__main__":
    host = config.FLASK_HOST
    port = config.FLASK_PORT
    
    print("\n" + "="*70)
    print("[Gurugram Traffic Prevention System]")
    print("="*70)
    print(f"Starting combined server + scheduler...")
    print("="*70)
    
    # Start scheduler first (as background thread)
    print("\n📊 Starting Traffic Data Collector...")
    start_scheduler_background()
    
    # Start server
    print(f"\n🚀 Starting Waitress Server")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   CORS Enabled: {config.CORS_ENABLED}")
    print(f"   CORS Origins: {config.CORS_ORIGINS}")
    print("\n" + "="*70 + "\n")
    
    try:
        serve(app, host=host, port=port)
    except KeyboardInterrupt:
        print("\n🛑 Server interrupted by user")
        sys.exit(0)

