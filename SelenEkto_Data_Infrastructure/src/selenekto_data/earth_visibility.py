"""Geometric Earth-disk visibility against a sampled lunar terrain horizon.

This module deliberately does not estimate radio-link availability. It consumes
Earth observer azimuth/elevation samples (for example from horizons.query_horizons)
and a terrain horizon profile already expressed in the DEM's grid-azimuth frame.
"""
from __future__ import annotations

import math
from typing import Any, Iterable

from .visibility import cyclic_interpolate

EARTH_ANGULAR_RADIUS_DEG = 0.95
GEOMETRIC_ONLY_WARNING = (
    "Geometric line-of-sight only; excludes antenna pointing/gain, link budget, "
    "ground-station availability, Earth-rotation station coverage, surface "
    "regolith/dust effects, and network scheduling."
)


def earth_disk_fraction_above_horizon(
    centre_clearance_deg: float,
    angular_radius_deg: float = EARTH_ANGULAR_RADIUS_DEG,
) -> float:
    """Approximate the fraction of Earth's apparent disk above a straight horizon.

    centre_clearance_deg is Earth-centre elevation minus terrain-horizon
    elevation at Earth's centre azimuth. The circular-segment approximation
    assumes the horizon is locally straight across the apparent disk.
    """
    clearance = float(centre_clearance_deg)
    radius = float(angular_radius_deg)
    if not math.isfinite(clearance):
        raise ValueError("centre_clearance_deg must be finite")
    if not math.isfinite(radius) or radius <= 0 or radius >= 90:
        raise ValueError("angular_radius_deg must be finite and between 0 and 90")
    if clearance >= radius:
        return 1.0
    if clearance <= -radius:
        return 0.0
    x = clearance / radius
    fraction = (math.acos(-x) + x * math.sqrt(1.0 - x * x)) / math.pi
    return min(1.0, max(0.0, fraction))


def _horizon_pairs(horizon_records: Iterable[dict[str, Any]]) -> list[tuple[float, float]]:
    pairs = []
    for record in horizon_records:
        azimuth = record.get("grid_azimuth_deg")
        elevation = record.get("horizon_angle_deg")
        if azimuth is None or elevation is None:
            raise ValueError("Horizon profile contains missing azimuth/elevation values")
        azimuth, elevation = float(azimuth), float(elevation)
        if not (math.isfinite(azimuth) and math.isfinite(elevation)):
            raise ValueError("Horizon profile contains non-finite values")
        pairs.append((azimuth, elevation))
    if len(pairs) < 2:
        raise ValueError("At least two terrain-horizon samples are required")
    return sorted(pairs)


def evaluate_earth_timeline(
    positions: Iterable[dict[str, Any]],
    horizon_records: Iterable[dict[str, Any]],
    grid_north_offset_deg: float,
    angular_radius_deg: float = EARTH_ANGULAR_RADIUS_DEG,
) -> list[dict[str, Any]]:
    """Classify Earth visibility at each ephemeris sample.

    Expected positions are rows from horizons.query_horizons (keys time_tag,
    azimuth_deg, elevation_deg). Rows produced by the existing experimental
    solar parser are also accepted (timestamp_utc, north_azimuth_deg, altitude_deg).

    grid_north_offset_deg is the angle, clockwise from projected +Y, of
    geographic/local north. The resulting bearing is compared with the
    terrain horizon's grid_azimuth_deg. This does not perform a lunar
    coordinate-frame transformation; callers must supply a validated offset
    and site coordinates compatible with the DEM.
    """
    offset = float(grid_north_offset_deg)
    if not math.isfinite(offset):
        raise ValueError("grid_north_offset_deg must be finite")
    earth_disk_fraction_above_horizon(0.0, angular_radius_deg)
    horizon = _horizon_pairs(horizon_records)
    output = []
    for position in positions:
        if "azimuth_deg" in position and "elevation_deg" in position:
            north_azimuth = float(position["azimuth_deg"])
            elevation = float(position["elevation_deg"])
        elif "north_azimuth_deg" in position and "altitude_deg" in position:
            north_azimuth = float(position["north_azimuth_deg"])
            elevation = float(position["altitude_deg"])
        else:
            raise ValueError("Each Earth position needs azimuth and elevation fields")
        if not (math.isfinite(north_azimuth) and 0 <= north_azimuth <= 360):
            raise ValueError("Earth azimuth must be finite and between 0 and 360 degrees")
        if not (math.isfinite(elevation) and -90 <= elevation <= 90):
            raise ValueError("Earth elevation must be finite and between -90 and 90 degrees")

        grid_azimuth = (north_azimuth + offset) % 360.0
        terrain_elevation = cyclic_interpolate(horizon, grid_azimuth)
        clearance = elevation - terrain_elevation
        visible_fraction = earth_disk_fraction_above_horizon(clearance, angular_radius_deg)
        output.append({
            "timestamp_utc": position.get("timestamp_utc", position.get("time_tag")),
            "north_azimuth_deg": north_azimuth,
            "grid_azimuth_deg": grid_azimuth,
            "earth_elevation_deg": elevation,
            "terrain_horizon_deg": terrain_elevation,
            "centre_clearance_deg": clearance,
            "earth_visible": visible_fraction > 0.0,
            "earth_fully_visible": visible_fraction >= 1.0,
            "visible_disk_fraction": visible_fraction,
            "visibility_model": "circular disk above locally straight terrain horizon",
            "visibility_scope": "geometric line-of-sight only",
        })
    if not output:
        raise ValueError("No Earth ephemeris positions were supplied")
    return output


def summarise_earth_timeline(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarise sampled geometric visibility; fractions are sample-based, not durations."""
    records = list(rows)
    if not records:
        raise ValueError("Cannot summarise an empty Earth visibility timeline")
    fractions = [float(row["visible_disk_fraction"]) for row in records]
    visible = sum(value > 0.0 for value in fractions)
    full = sum(value >= 1.0 for value in fractions)
    return {
        "sample_count": len(records),
        "samples_with_any_earth_visibility": visible,
        "samples_with_full_earth_disk_visibility": full,
        "visible_sample_fraction": visible / len(records),
        "mean_visible_disk_fraction": sum(fractions) / len(fractions),
        "minimum_visible_disk_fraction": min(fractions),
        "maximum_visible_disk_fraction": max(fractions),
        "interpretation": "Sample fractions are not time durations; sampling cadence controls temporal resolution.",
        "warning": GEOMETRIC_ONLY_WARNING,
    }
