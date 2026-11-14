"""Independent per-candidate DEM horizon profiles (not sunlight or landing safety)."""
from __future__ import annotations
import csv
import math
from pathlib import Path


def parse_candidates(csv_path, width, height):
    """Read map-exported cells, rejecting invalid or duplicate pixel coordinates."""
    with Path(csv_path).open(newline='', encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        if not reader.fieldnames or not {'row','col'}.issubset(reader.fieldnames):
            raise ValueError('Candidate CSV must include row and col columns')
        rows=list(reader)
    if not rows:
        raise ValueError('Candidate CSV is empty. Add points in the terrain map first.')
    if len(rows)>25:
        raise ValueError('Use at most 25 candidates per run')
    result=[]; seen=set()
    for i,r in enumerate(rows,1):
        try:
            row,col=int(r['row']),int(r['col'])
        except (ValueError,TypeError) as e:
            raise ValueError(f'Invalid row/col at candidate {i}') from e
        if not (0 <= row < height and 0 <= col < width):
            raise ValueError(f'Candidate {i} falls outside the DEM')
        if (row,col) in seen:
            raise ValueError(f'Duplicate candidate pixel at row {row}, col {col}')
        seen.add((row,col))
        result.append({'name':r.get('name') or f'Candidate {i:02d}', 'row':row, 'col':col})
    return result


def summarize_profile(records):
    angles=[r['horizon_angle_deg'] for r in records if r['horizon_angle_deg'] is not None]
    if not angles:
        raise ValueError('No valid horizon angles for candidate')
    distances=[r['controlling_distance_m'] for r in records if r['controlling_distance_m'] is not None]
    return {'directions':len(angles),'mean_horizon_deg':round(sum(angles)/len(angles),6),
            'minimum_horizon_deg':round(min(angles),6), 'maximum_horizon_deg':round(max(angles),6),
            'furthest_controlling_cell_m':max(distances),
            'zero_lola_controlling_directions':sum(r['controlling_measurement_count']==0 for r in records),
            'edge_truncated_directions':sum(r['boundary_truncated'] for r in records),
            'missing_sample_directions':sum(r['missing_elevation_samples']>0 for r in records)}
