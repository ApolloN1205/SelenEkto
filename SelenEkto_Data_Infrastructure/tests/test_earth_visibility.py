import pytest

from selenekto_data.earth_visibility import (
    GEOMETRIC_ONLY_WARNING,
    earth_disk_fraction_above_horizon,
    evaluate_earth_timeline,
    summarise_earth_timeline,
)


def flat_horizon(value=0.0):
    return [
        {"grid_azimuth_deg": float(az), "horizon_angle_deg": float(value)}
        for az in range(0, 360)
    ]


def test_disk_fraction_limits_and_half_disk():
    assert earth_disk_fraction_above_horizon(2.0) == 1.0
    assert earth_disk_fraction_above_horizon(-2.0) == 0.0
    assert earth_disk_fraction_above_horizon(0.0) == pytest.approx(0.5)


def test_disk_fraction_is_symmetric():
    above = earth_disk_fraction_above_horizon(0.4)
    below = earth_disk_fraction_above_horizon(-0.4)
    assert above + below == pytest.approx(1.0)


def test_invalid_disk_radius_rejected():
    with pytest.raises(ValueError):
        earth_disk_fraction_above_horizon(0, 0)
    with pytest.raises(ValueError):
        earth_disk_fraction_above_horizon(0, 90)


def test_earth_direction_is_rotated_into_grid_frame():
    positions = [{
        "time_tag": "2026-Nov-15 12:00",
        "azimuth_deg": 350.0,
        "elevation_deg": 1.2,
    }]
    horizon = flat_horizon()
    horizon[10]["horizon_angle_deg"] = 2.0
    rows = evaluate_earth_timeline(positions, horizon, 20.0)
    assert rows[0]["grid_azimuth_deg"] == pytest.approx(10.0)
    assert rows[0]["terrain_horizon_deg"] == pytest.approx(2.0)
    assert rows[0]["visible_disk_fraction"] == pytest.approx(0.5)


def test_accepts_existing_solar_parser_field_names():
    rows = evaluate_earth_timeline(
        [{"timestamp_utc": "2026-11-15T12:00:00Z",
          "north_azimuth_deg": 90.0, "altitude_deg": 3.0}],
        flat_horizon(1.0),
        0.0,
    )
    assert rows[0]["earth_fully_visible"] is True
    assert rows[0]["visible_disk_fraction"] == 1.0


def test_rejects_incomplete_horizon_and_bad_ephemeris():
    with pytest.raises(ValueError):
        evaluate_earth_timeline(
            [{"azimuth_deg": 10, "elevation_deg": 2}],
            [{"grid_azimuth_deg": 0, "horizon_angle_deg": None}],
            0,
        )
    with pytest.raises(ValueError):
        evaluate_earth_timeline(
            [{"azimuth_deg": 361, "elevation_deg": 2}],
            flat_horizon(),
            0,
        )


def test_summary_is_sample_based_and_disclaims_radio_link():
    rows = evaluate_earth_timeline(
        [
            {"azimuth_deg": 0, "elevation_deg": 2},
            {"azimuth_deg": 90, "elevation_deg": 0},
            {"azimuth_deg": 180, "elevation_deg": -2},
        ],
        flat_horizon(),
        0,
    )
    summary = summarise_earth_timeline(rows)
    assert summary["sample_count"] == 3
    assert summary["samples_with_any_earth_visibility"] == 2
    assert summary["samples_with_full_earth_disk_visibility"] == 1
    assert summary["mean_visible_disk_fraction"] == pytest.approx(
        sum(row["visible_disk_fraction"] for row in rows) / 3
    )
    assert "link budget" in GEOMETRIC_ONLY_WARNING
