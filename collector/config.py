# collector/config.py
"""
Collector configuration - imports from global project config.
This module maintains backward compatibility while centralizing configuration.
"""

from pathlib import Path
import sys

# Add parent directory to path to import global config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import TOMTOM_API_KEY, MONITOR_POINTS, COLLECTOR_INTERVAL_MIN

# Re-export for backward compatibility
__all__ = ["TOMTOM_API_KEY", "MONITOR_POINTS", "COLLECTOR_INTERVAL_MIN"]
