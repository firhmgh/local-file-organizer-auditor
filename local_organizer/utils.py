"""
Utility functions for formatting, file system helpers, and terminal printing.
"""
import os
import math
import datetime
from pathlib import Path
from typing import Optional


def format_bytes(size_bytes: int) -> str:
    """Format bytes into a human-readable string (B, KB, MB, GB, TB)."""
    if size_bytes <= 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {units[i]}"


def format_timestamp(ts: float) -> str:
    """Format timestamp into readable date time."""
    try:
        dt = datetime.datetime.fromtimestamp(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "N/A"


def normalize_path(path: str) -> str:
    """Normalize a path to a consistent string representation."""
    return os.path.normpath(os.path.abspath(path))


def is_path_relative_to(path: Path, base: Path) -> bool:
    """Safely check if path is relative to base (compatible with older python)."""
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except (ValueError, RuntimeError):
        return False
