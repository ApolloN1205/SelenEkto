"""Utilities for inspecting NASA PGDA Site01 projected DEM cells.

No physical landing-safety determination is made by this module.
"""
from __future__ import annotations
import math


def xy_to_cell(transform, x: float, y: float, width: int, height: int) -> tuple[int, int] | None:
    """Return raster (row, col) or None if the projected point lies outside."""
    if not math.isfinite(x) or not math.isfinite(y):
        return None
    col_f, row_f = (~transform) * (x, y)
    row, col = math.floor(row_f), math.floor(col_f)
    if 0 <= row < height and 0 <= col < width:
        return row, col
    return None


def centre_xy(transform, row: int, col: int) -> tuple[float, float]:
    return transform * (col + 0.5, row + 0.5)


def terrain_record(row: int, col: int, values: dict[str, float], transform) -> dict:
    x, y = centre_xy(transform, row, col)
    record = {'row': row, 'col': col, 'x_projected_m': round(x, 3), 'y_projected_m': round(y, 3)}
    for key in ('elevation_m', 'slope_deg', 'elevation_rms_m', 'slope_rms_deg', 'lola_spot_count'):
        v = values.get(key)
        record[key] = round(float(v), 6) if v is not None and math.isfinite(float(v)) else None
    return record
