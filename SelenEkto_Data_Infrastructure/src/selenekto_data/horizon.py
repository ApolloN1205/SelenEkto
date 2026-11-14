"""Prototype DEM-limited lunar terrain horizon (grid-relative azimuths).

No illumination, landing safety, or full-Moon horizon is inferred here.
"""
from __future__ import annotations

import math

import numpy as np
from rasterio.transform import rowcol

MOON_RADIUS_M = 1_737_400.0


def terrain_angle_deg(distance_m: float, ground_elevation_m: float,
                      target_elevation_m: float, observer_height_m: float = 0.0,
                      moon_radius_m: float = MOON_RADIUS_M) -> float:
    """Angle from the observer's local horizontal to another lunar surface point.

    distance_m is modelled as surface arc distance. Both elevations are relative
    to the same spherical reference radius. Uses spherical geometry.
    """
    if distance_m <= 0 or moon_radius_m <= 0 or observer_height_m < 0:
        raise ValueError("Distances/radius must be positive; observer height nonnegative")
    a = distance_m / moon_radius_m
    rt = moon_radius_m + target_elevation_m
    ro = moon_radius_m + ground_elevation_m + observer_height_m
    return math.degrees(math.atan2(rt * math.cos(a) - ro, rt * math.sin(a)))


def calculate_horizon(dem, transform, origin_x: float, origin_y: float,
                      max_distance_m: float = 5000.0, sample_step_m: float = 10.0,
                      azimuth_step_deg: float = 1.0, observer_height_m: float = 0.0,
                      moon_radius_m: float = MOON_RADIUS_M,
                      counts=None, errors=None) -> list[dict]:
    """Sample the 2-D raster along XY rays and keep the highest apparent terrain.

    Azimuth is clockwise from PROJECTED +Y, not geographic true north.
    Inputs assume a north-up projected grid in metres and no rotation/skew.
    """
    if dem.ndim != 2 or not np.isfinite(dem).any():
        raise ValueError("DEM must be a 2-D array with finite elevations")
    if max_distance_m <= 0 or sample_step_m <= 0 or not 0 < azimuth_step_deg <= 360:
        raise ValueError("Invalid scan settings")
    if observer_height_m < 0 or moon_radius_m <= 0:
        raise ValueError("Invalid observer height or Moon radius")
    if not (abs(transform.b) < 1e-10 and abs(transform.d) < 1e-10
            and transform.a > 0 and transform.e < 0):
        raise ValueError("Only north-up, non-rotated grids are supported")
    if counts is not None and counts.shape != dem.shape:
        raise ValueError("Counts grid shape does not match DEM")
    if errors is not None and errors.shape != dem.shape:
        raise ValueError("Uncertainty grid shape does not match DEM")
    origin_row, origin_col = rowcol(transform, origin_x, origin_y)
    if not (0 <= origin_row < dem.shape[0] and 0 <= origin_col < dem.shape[1]):
        raise ValueError("Observer location outside DEM")
    ground = float(dem[origin_row, origin_col])
    if not math.isfinite(ground):
        raise ValueError("No valid elevation at observer location")

    # Start at >= 1 raster pixel to avoid re-sampling the origin cell.
    start = max(abs(transform.a), abs(transform.e), sample_step_m)
    distances = np.arange(start, max_distance_m + 1e-9, sample_step_m)
    if len(distances) == 0:
        raise ValueError("Scan radius is shorter than one sampling step")
    records = []
    azimuths = np.arange(0, 360, azimuth_step_deg)
    for azimuth in azimuths:
        a = np.deg2rad(azimuth)
        xs = origin_x + distances * np.sin(a)
        ys = origin_y + distances * np.cos(a)
        # Equivalent to rasterio rowcol for north-up grids, vectorised.
        cols = np.floor((xs - transform.c) / transform.a).astype(int)
        rows = np.floor((ys - transform.f) / transform.e).astype(int)
        within = ((rows >= 0) & (rows < dem.shape[0]) &
                  (cols >= 0) & (cols < dem.shape[1]))
        # A ray must terminate at the first grid boundary.
        outside = np.flatnonzero(~within)
        endpoint_index = int(outside[0]) if len(outside) else len(distances)
        rows, cols = rows[:endpoint_index], cols[:endpoint_index]
        sampled_d = distances[:endpoint_index]
        z = dem[rows, cols]
        valid = np.isfinite(z)
        good = np.flatnonzero(valid)
        if len(good):
            di = sampled_d[good]
            zz = z[good]
            arc = di / moon_radius_m
            target_radius = moon_radius_m + zz
            observer_radius = moon_radius_m + ground + observer_height_m
            angles = np.degrees(np.arctan2(target_radius * np.cos(arc) - observer_radius,
                                            target_radius * np.sin(arc)))
            best = int(np.argmax(angles))
            idx = int(good[best])
            peak_row, peak_col = int(rows[idx]), int(cols[idx])
            winner = {
                "horizon_angle_deg": round(float(angles[best]), 6),
                "controlling_distance_m": float(sampled_d[idx]),
                "controlling_elevation_m": float(z[idx]),
                "controlling_row": peak_row,
                "controlling_col": peak_col,
                "controlling_measurement_count": (float(counts[peak_row, peak_col])
                                                 if counts is not None and np.isfinite(counts[peak_row, peak_col]) else None),
                "controlling_elevation_rms_error_m": (float(errors[peak_row, peak_col])
                                                  if errors is not None and np.isfinite(errors[peak_row, peak_col]) else None),
            }
        else:
            winner = {k: None for k in ("horizon_angle_deg", "controlling_distance_m",
                                          "controlling_elevation_m", "controlling_row", "controlling_col",
                                          "controlling_measurement_count", "controlling_elevation_rms_error_m")}
        records.append({
            "grid_azimuth_deg": round(float(azimuth), 5),
            **winner,
            "sampled_pixels": int(len(sampled_d)),
            "valid_elevation_samples": int(valid.sum()),
            "missing_elevation_samples": int((~valid).sum()),
            "boundary_truncated": bool(len(outside)),
            "distance_scanned_m": float(sampled_d[-1]) if len(sampled_d) else 0.0,
        })
    return records
