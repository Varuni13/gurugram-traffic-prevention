# server/utils.py
"""
Utility functions for the API server.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

# Import global config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as global_config


def find_roads_file() -> Optional[Path]:
    """Find the first available roads GeoJSON file."""
    for p in global_config.ROADS_CANDIDATES:
        if p.exists():
            return p
    return None


def find_graph_file() -> Optional[Path]:
    """Find the first available graph file."""
    for p in global_config.GRAPH_CANDIDATES:
        if p.exists():
            return p
    return None


def atomic_write_json(path: Path, payload: dict) -> None:
    """
    Write JSON safely: write temp -> replace.
    Prevents reading half-written JSON files.
    
    Args:
        path: Target file path
        payload: Dictionary to serialize as JSON
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def atomic_read_json(path: Path) -> Dict[str, Any]:
    """
    Read JSON safely.
    
    Args:
        path: File path to read
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If file is not valid JSON
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
