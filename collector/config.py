# collector/config.py
"""
Collector configuration - imports from global project config.
This module maintains backward compatibility while centralizing configuration.
"""

from pathlib import Path
import sys
import importlib.util

# Load the PARENT config.py explicitly to avoid self-import when running from collector/
_parent_config_path = Path(__file__).resolve().parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("project_config", _parent_config_path)
_project_config = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_project_config)

TOMTOM_API_KEY = _project_config.TOMTOM_API_KEY
MONITOR_POINTS = _project_config.MONITOR_POINTS
COLLECTOR_INTERVAL_MIN = _project_config.COLLECTOR_INTERVAL_MIN

# Re-export for backward compatibility
__all__ = ["TOMTOM_API_KEY", "MONITOR_POINTS", "COLLECTOR_INTERVAL_MIN"]
