import json
import glob
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


SNAPSHOT_GLOB = "all_courses_data_*.json"


def _parse_timestamp_from_filename(path: Path) -> Optional[datetime]:
    """Extract timestamp from filename pattern all_courses_data_YYYYMMDD_HHMMSS.json"""
    try:
        stem = path.stem  # all_courses_data_YYYYMMDD_HHMMSS
        ts = stem.replace("all_courses_data_", "")
        return datetime.strptime(ts, "%Y%m%d_%H%M%S")
    except Exception:
        return None


def list_snapshot_files(data_dir: str = "data") -> List[Path]:
    """List snapshot files in the data directory, newest first."""
    base = Path(data_dir)
    files = [Path(p) for p in glob.glob(str(base / SNAPSHOT_GLOB))]
    files.sort(key=lambda p: _parse_timestamp_from_filename(p) or datetime.min, reverse=True)
    return files


def get_all_snapshots(data_dir: str = "data") -> List[Dict[str, Any]]:
    """Return snapshots as a list of dicts: { 'Date': ISO8601, 'Data': <json> }, newest first."""
    snapshots: List[Dict[str, Any]] = []
    for f in list_snapshot_files(data_dir):
        try:
            dt = _parse_timestamp_from_filename(f)
            if not dt:
                continue
            with open(f, "r") as fh:
                data = json.load(fh)
            snapshots.append({
                "Date": dt.replace(microsecond=0).isoformat(),
                "Data": data,
            })
        except Exception:
            # Skip files we cannot parse/read
            continue
    return snapshots


def get_latest_snapshot_data(data_dir: str = "data") -> Optional[Dict[str, Any]]:
    """Return the Data payload from the latest snapshot, or None."""
    snaps = get_all_snapshots(data_dir)
    if not snaps:
        return None
    return snaps[0]["Data"]


def get_latest_snapshots(count: int = 2, data_dir: str = "data") -> List[Dict[str, Any]]:
    """Return the latest N snapshots (newest first)."""
    snaps = get_all_snapshots(data_dir)
    return snaps[:count]

