"""
Smart Traffic Data Collector Scheduler
=======================================
Optimized to stay within TomTom's free 2,500 calls/day limit.

Schedule:
- Peak hours (6 AM - 9 PM):   Every 10 minutes  → 90 calls/point × 25 points = 2,250 calls
- Off-peak (9 PM - 6 AM):     Every 60 minutes  → 9 calls/point × 25 points  = 225 calls
- Total daily calls: ~2,475 (within 2,500 limit)

Usage:
    python collector/run_scheduler.py              # Run in foreground
    python collector/run_scheduler.py --daemon     # Run as background process (Windows)
    python collector/run_scheduler.py --status     # Check if running
"""

import os
import sys
import time
import signal
import subprocess
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================
PEAK_START_HOUR = 6      # 6 AM
PEAK_END_HOUR = 21       # 9 PM

PEAK_INTERVAL_MIN = 10   # Every 10 minutes during peak
OFFPEAK_INTERVAL_MIN = 60  # Every 60 minutes during off-peak

# PID file for tracking running instance
PID_FILE = Path(__file__).parent / "scheduler.pid"
LOG_FILE = Path(__file__).parent / "outputs" / "scheduler.log"

# ============================================================================
# HELPERS
# ============================================================================
def is_peak_hour() -> bool:
    """Check if current time is within peak traffic hours."""
    current_hour = datetime.now().hour
    return PEAK_START_HOUR <= current_hour < PEAK_END_HOUR


def get_current_interval() -> int:
    """Get the appropriate interval based on time of day."""
    return PEAK_INTERVAL_MIN if is_peak_hour() else OFFPEAK_INTERVAL_MIN


def get_next_run_time(interval_min: int) -> datetime:
    """Calculate next run time aligned to interval boundaries."""
    now = datetime.now()
    # Align to interval boundaries (e.g., :00, :10, :20 for 10-min interval)
    minutes_past = now.minute % interval_min
    if minutes_past == 0 and now.second == 0:
        return now
    next_run = now.replace(second=0, microsecond=0) + timedelta(minutes=interval_min - minutes_past)
    return next_run


def log(message: str):
    """Log message to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    
    # Also write to log file
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except Exception:
        pass  # Don't fail if logging fails


def collect_traffic():
    """Run the traffic collection script."""
    collector_script = Path(__file__).parent / "collect_tomtom.py"
    project_root = Path(__file__).parent.parent
    
    try:
        result = subprocess.run(
            [sys.executable, str(collector_script)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if result.returncode == 0:
            log("✅ Collection completed successfully")
        else:
            log(f"⚠️ Collection finished with warnings: {result.stderr[:200] if result.stderr else 'unknown'}")
    except subprocess.TimeoutExpired:
        log("❌ Collection timed out after 5 minutes")
    except Exception as e:
        log(f"❌ Collection failed: {e}")


def write_pid():
    """Write current process ID to file."""
    PID_FILE.write_text(str(os.getpid()))


def read_pid() -> int | None:
    """Read PID from file, return None if not found."""
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, OSError):
            return None
    return None


def is_process_running(pid: int) -> bool:
    """Check if a process with given PID is running."""
    try:
        # Windows-specific check
        import ctypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        # Fallback: try to use tasklist
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True
            )
            return str(pid) in result.stdout
        except Exception:
            return False


def cleanup_pid():
    """Remove PID file on exit."""
    if PID_FILE.exists():
        PID_FILE.unlink()


# ============================================================================
# MAIN SCHEDULER LOOP
# ============================================================================
def run_scheduler():
    """Main scheduler loop with smart peak/off-peak intervals."""
    
    # Check if already running
    existing_pid = read_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"⚠️ Scheduler already running (PID: {existing_pid})")
        print(f"   Stop it first or check status with: python run_scheduler.py --status")
        sys.exit(1)
    
    # Write our PID
    write_pid()
    
    # Handle graceful shutdown (only works in main thread)
    def signal_handler(signum, frame):
        log("🛑 Received shutdown signal, cleaning up...")
        cleanup_pid()
        sys.exit(0)
    
    # Only register signal handlers if running in main thread
    import threading
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    log("=" * 60)
    log("🚀 Smart Traffic Scheduler Started")
    log(f"   Peak hours ({PEAK_START_HOUR}:00 - {PEAK_END_HOUR}:00): Every {PEAK_INTERVAL_MIN} min")
    log(f"   Off-peak: Every {OFFPEAK_INTERVAL_MIN} min")
    log(f"   PID: {os.getpid()}")
    log("=" * 60)
    
    collection_count = 0
    daily_reset_date = datetime.now().date()
    
    try:
        while True:
            # Reset daily counter at midnight
            if datetime.now().date() != daily_reset_date:
                log(f"📊 Daily summary: {collection_count} collections yesterday")
                collection_count = 0
                daily_reset_date = datetime.now().date()
            
            # Determine current interval
            interval = get_current_interval()
            period = "🌞 PEAK" if is_peak_hour() else "🌙 OFF-PEAK"
            
            # Collect traffic data
            log(f"{period} | Interval: {interval} min | Starting collection #{collection_count + 1}...")
            collect_traffic()
            collection_count += 1
            
            # Calculate sleep time (align to interval boundaries)
            next_run = get_next_run_time(interval)
            sleep_seconds = (next_run - datetime.now()).total_seconds()
            
            # Handle edge case where next_run is in the past
            if sleep_seconds < 0:
                sleep_seconds = interval * 60
            
            log(f"💤 Next collection at {next_run.strftime('%H:%M:%S')} ({interval} min interval)")
            
            # Sleep in small chunks to allow for interval changes at peak/off-peak boundaries
            sleep_end = datetime.now() + timedelta(seconds=sleep_seconds)
            while datetime.now() < sleep_end:
                # Check every 30 seconds if we need to adjust
                remaining = (sleep_end - datetime.now()).total_seconds()
                chunk = min(30, remaining)
                if chunk > 0:
                    time.sleep(chunk)
                
                # If we crossed a peak/off-peak boundary, recalculate
                new_interval = get_current_interval()
                if new_interval != interval:
                    log(f"⏰ Interval changed to {new_interval} min (crossed peak/off-peak boundary)")
                    break
                    
    except KeyboardInterrupt:
        log("🛑 Scheduler stopped by user")
    finally:
        cleanup_pid()


def check_status():
    """Check if scheduler is running."""
    pid = read_pid()
    if pid and is_process_running(pid):
        print(f"✅ Scheduler is RUNNING (PID: {pid})")
        print(f"   Log file: {LOG_FILE}")
        
        # Show last few log lines
        if LOG_FILE.exists():
            lines = LOG_FILE.read_text().strip().split("\n")
            print(f"\n   Last 5 log entries:")
            for line in lines[-5:]:
                print(f"   {line}")
    else:
        print("❌ Scheduler is NOT RUNNING")
        if PID_FILE.exists():
            print("   (Stale PID file found, cleaning up...)")
            PID_FILE.unlink()


def stop_scheduler():
    """Stop running scheduler."""
    pid = read_pid()
    if pid and is_process_running(pid):
        try:
            os.kill(pid, signal.SIGTERM)
            print(f"✅ Sent stop signal to scheduler (PID: {pid})")
            time.sleep(1)
            if not is_process_running(pid):
                print("   Scheduler stopped successfully")
                cleanup_pid()
            else:
                print("   Scheduler may still be shutting down...")
        except Exception as e:
            print(f"❌ Failed to stop scheduler: {e}")
    else:
        print("❌ Scheduler is not running")
        if PID_FILE.exists():
            PID_FILE.unlink()


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Smart Traffic Data Collector Scheduler")
    parser.add_argument("--status", action="store_true", help="Check if scheduler is running")
    parser.add_argument("--stop", action="store_true", help="Stop the running scheduler")
    parser.add_argument("--daemon", action="store_true", help="Run as background process")
    
    args = parser.parse_args()
    
    if args.status:
        check_status()
    elif args.stop:
        stop_scheduler()
    elif args.daemon:
        # On Windows, use pythonw or start in background
        print("Starting scheduler in background...")
        script_path = Path(__file__).resolve()
        project_root = script_path.parent.parent
        
        # Use 'start' command to run in background on Windows
        subprocess.Popen(
            f'start /B "" "{sys.executable}" "{script_path}"',
            shell=True,
            cwd=str(project_root),
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        print("✅ Scheduler started in background")
        print(f"   Check status: python collector/run_scheduler.py --status")
        print(f"   Stop:         python collector/run_scheduler.py --stop")
        print(f"   Log file:     {LOG_FILE}")
    else:
        run_scheduler()
