"""Read existing Site01 terrain results and compare user-supplied direction/altitude.

No solar ephemeris is calculated here; bearings MUST use DEM grid convention.
"""
from __future__ import annotations
import csv
import json
import math
from pathlib import Path


def read_site_results(horizon_file, uncertainty_file=None):
    horizon = json.loads(Path(horizon_file).read_text(encoding='utf-8'))
    records = horizon['angles']
    if not records or any('grid_azimuth_deg' not in r for r in records):
        raise ValueError('Invalid horizon records')
    points = sorted((float(r['grid_azimuth_deg']), r['horizon_angle_deg']) for r in records)
    if any(angle is None or not math.isfinite(float(angle)) for _, angle in points):
        raise ValueError('Horizon contains unavailable/nonfinite angles')
    uncertainties = None
    if uncertainty_file:
        data = json.loads(Path(uncertainty_file).read_text(encoding='utf-8'))
        uncertainties = sorted((float(r['grid_azimuth_deg']),
                                r['low_scenario_angle_deg'], r['high_scenario_angle_deg'])
                               for r in data['directions'])
        if len(uncertainties) != len(points) or any(abs(u[0]-p[0])>1e-6 for u,p in zip(uncertainties,points)):
            raise ValueError('Horizon and uncertainty direction grids do not match')
        if any(x is None or y is None for _, x, y in uncertainties):
            raise ValueError('Uncertainty records contain missing angles')
        h_settings = horizon.get('settings', {})
        u_settings = data.get('settings', {})
        for k1,k2 in (('max_distance_m','max_distance_m'),('sample_step_m','sample_step_m'),('azimuth_step_deg','azimuth_step_deg'),('observer_height_m','observer_height_m')):
            if k1 in h_settings and k2 in u_settings and abs(float(h_settings[k1])-float(u_settings[k2]))>1e-7:
                raise ValueError(f'Uncertainty has different {k1} setting')
    return horizon, points, uncertainties


def cyclic_interpolate(points, azimuth, value_index=1):
    """Linearly interpolate cyclic grid azimuth samples. No spatial north conversion."""
    if not math.isfinite(float(azimuth)):
        raise ValueError('Direction must be finite')
    if len(points) < 2:
        raise ValueError('At least two horizon samples required')
    x = float(azimuth) % 360
    ordered = sorted(points)
    xs = [float(p[0]) % 360 for p in ordered]
    if any(xs[i]>=xs[i+1] for i in range(len(xs)-1)):
        raise ValueError('Duplicate or unsorted circular directions')
    if x < xs[0]:
        left = (xs[-1] - 360, ordered[-1][value_index])
        right = (xs[0], ordered[0][value_index])
    elif x >= xs[-1]:
        left = (xs[-1], ordered[-1][value_index])
        right = (xs[0]+360, ordered[0][value_index])
    else:
        import bisect
        i = bisect.bisect_right(xs, x)
        left = (xs[i-1], ordered[i-1][value_index])
        right = (xs[i], ordered[i][value_index])
    frac = (x-left[0]) / (right[0]-left[0])
    return float(left[1]) + frac * (float(right[1])-float(left[1]))


def classify_sky_position(points, uncertainty, direction_deg, altitude_deg):
    """Classify relative to sampled horizon scenarios; no ephemeris implied."""
    altitude = float(altitude_deg)
    if not math.isfinite(altitude) or not -90 <= altitude <= 90:
        raise ValueError('Altitude must be between -90 and +90 degrees')
    baseline = cyclic_interpolate(points, direction_deg)
    lower = cyclic_interpolate(uncertainty, direction_deg, 1) if uncertainty else None
    higher = cyclic_interpolate(uncertainty, direction_deg, 2) if uncertainty else None
    if lower is None:
        status = 'ABOVE baseline horizon' if altitude > baseline else ('AT baseline horizon' if altitude == baseline else 'BELOW baseline horizon')
    elif altitude > higher:
        status = 'ABOVE all modelled scenarios'
    elif altitude < lower:
        status = 'BELOW all modelled scenarios'
    else:
        status = 'SCENARIO-DEPENDENT / UNCERTAIN'
    return {'grid_direction_deg': float(direction_deg) % 360, 'sky_altitude_deg': altitude,
            'baseline_horizon_deg': baseline, 'low_scenario_horizon_deg': lower,
            'high_scenario_horizon_deg': higher, 'status': status}


def evaluate_csv(csv_path, points, uncertainty):
    """Import precomputed or hypothetical sky positions with grid-relative direction.
    Header: timestamp_utc,grid_azimuth_deg,altitude_deg
    """
    out=[]
    with Path(csv_path).open(encoding='utf-8-sig', newline='') as handle:
        reader=csv.DictReader(handle)
        required={'timestamp_utc','grid_azimuth_deg','altitude_deg'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('CSV requires timestamp_utc,grid_azimuth_deg,altitude_deg')
        for row in reader:
            from datetime import datetime
            stamp=row['timestamp_utc'].strip()
            dt=datetime.fromisoformat(stamp.replace('Z','+00:00'))
            if dt.tzinfo is None:
                raise ValueError('timestamp_utc must contain timezone / Z')
            result=classify_sky_position(points,uncertainty,float(row['grid_azimuth_deg']),float(row['altitude_deg']))
            out.append({'timestamp_utc':dt.isoformat(), **result})
    if not out:
        raise ValueError('CSV is empty')
    return out
