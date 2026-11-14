"""Shared, GUI-free operations for safe comparisons and download URL building."""
from __future__ import annotations
from pathlib import Path
from urllib.parse import quote
import math

PGDA_ROOT = "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/"


def pgda_url(region: str, file_name: str) -> str:
    """NASA links nest GeoTIFFs in a directory matching the region ID."""
    if not region or not region.isalnum() or not file_name.startswith(region + "_final_adj_5mpp_") or not file_name.endswith(".tif"):
        raise ValueError("Unexpected NASA region or filename")
    return f"{PGDA_ROOT}{quote(region)}/{quote(file_name)}"


def comparable_candidates(records: list[dict], indices: list[int]) -> list[dict]:
    if len(indices) < 2:
        raise ValueError("Select at least two named candidates to compare")
    if len(set(indices)) != len(indices) or any(i < 0 or i >= len(records) for i in indices):
        raise ValueError("Invalid selected candidate row")
    return [records[i] for i in indices]


def valid_value(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        v = float(value)
    except (ValueError, TypeError):
        return None
    return v if math.isfinite(v) else None


def candidate_display(record: dict) -> str:
    return f"{record.get('region','?')} | {record.get('name','Unnamed')} | ({record.get('row','?')}, {record.get('col','?')})"


def save_path(root: Path) -> Path:
    return Path(root) / "data" / "processed" / "unified" / "saved_named_candidates.csv"
