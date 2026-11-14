import math

import numpy as np
import pytest
from rasterio.transform import from_origin

from selenekto_data.horizon import calculate_horizon, terrain_angle_deg


def test_flat_moon_has_curvature_below_zero():
    assert terrain_angle_deg(1000, 0, 0) < 0
    assert -0.02 < terrain_angle_deg(1000, 0, 0) < 0


def test_higher_target_increases_angle():
    assert terrain_angle_deg(1000, 0, 100) > terrain_angle_deg(1000, 0, 0)


def test_higher_observer_decreases_angle():
    assert terrain_angle_deg(1000, 0, 0, observer_height_m=2) < terrain_angle_deg(1000, 0, 0)


def test_known_eastward_ridge_is_detected():
    dem = np.zeros((101, 101), dtype=float)
    dem[50, 60] = 100
    tfm = from_origin(-505, 505, 10, 10)
    result = calculate_horizon(dem, tfm, 0, 0, max_distance_m=200,
                               sample_step_m=10, azimuth_step_deg=90)
    # +X is 90 degrees. At around 100 m, the ridge is nearly 45 degrees up.
    east = next(r for r in result if r["grid_azimuth_deg"] == 90)
    assert east["horizon_angle_deg"] > 40
    assert east["controlling_elevation_m"] == 100
    north = next(r for r in result if r["grid_azimuth_deg"] == 0)
    assert north["horizon_angle_deg"] < 0


def test_grid_edge_reports_truncation():
    dem = np.zeros((11, 11), dtype=float)
    tfm = from_origin(-55, 55, 10, 10)
    r = calculate_horizon(dem, tfm, 0, 0, max_distance_m=200, sample_step_m=10,
                          azimuth_step_deg=90)
    assert all(d["boundary_truncated"] for d in r)


def test_bad_observer_coordinate_rejected():
    with pytest.raises(ValueError, match="outside"):
        calculate_horizon(np.zeros((11, 11)), from_origin(-55, 55, 10, 10),
                          1000, 1000, 100, 10, 90)
