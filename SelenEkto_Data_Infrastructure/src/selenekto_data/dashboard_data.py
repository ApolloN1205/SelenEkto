"""Read-only discovery and candidate-summary helpers for the SelenEkto desktop dashboard."""
from __future__ import annotations
import json
from pathlib import Path


def discover_regions(raw_root: Path):
    """Find local regions that have a matching elevation and slope raster."""
    found=[]
    if not raw_root.is_dir():return found
    for region in sorted(raw_root.iterdir()):
        if not region.is_dir():continue
        name=region.name
        elevation=region/f'{name}_final_adj_5mpp_surf.tif'
        slope=region/f'{name}_final_adj_5mpp_slp.tif'
        if elevation.is_file() and slope.is_file():found.append(name)
    return found


def read_candidate_comparison(file: Path):
    """Read existing candidate solar JSON, never invent missing results."""
    if not file.is_file():return []
    data=json.loads(file.read_text(encoding='utf-8'))
    rows=data.get('comparison',[])
    if not isinstance(rows,list):raise ValueError('Invalid candidate comparison format')
    return rows


def latest_candidate_report(root: Path):
    if not root.is_dir():return None
    reports=list(root.glob('*/candidate_solar_comparison.json'))
    return max(reports,key=lambda p:p.stat().st_mtime) if reports else None


def normalized_weight_label(sun,slope,uncertainty):
    weights=(float(sun),float(slope),float(uncertainty))
    if any(w<0 or w>10 for w in weights) or sum(weights)<=0:
        raise ValueError('Weights must be 0–10 with at least one positive value')
    return weights


def candidate_label(row):
    return f"{row.get('name','Unnamed')} · ({row.get('row','?')}, {row.get('col','?')})"
