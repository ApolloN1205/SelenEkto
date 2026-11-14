import pytest

from selenekto_data.horizons import (
    HorizonsError, build_query_params, parse_observer_result,
    signed_east_to_0_360,
)

SAMPLE = """Synthetic test response only; not a real NASA observation.
$$SOE
2026-Nov-14 00:00, 125.0000, 12.5000,
2026-Nov-14 00:10, 126.2500, 12.2500,
$$EOE
"""


def test_parser_extracts_azimuth_and_elevation_from_synthetic_fixture():
    rows = parse_observer_result(SAMPLE)
    assert len(rows) == 2
    assert rows[0]["azimuth_deg"] == 125.0
    assert rows[0]["elevation_deg"] == 12.5
    assert rows[1]["time_tag"] == "2026-Nov-14 00:10"


def test_parser_rejects_missing_markers():
    with pytest.raises(HorizonsError):
        parse_observer_result("not a horizons response")


def test_query_params_use_lunar_surface_observer_and_quantity_four():
    params = build_query_params(
        target="sun", longitude_east_deg=222.51, latitude_deg=-89.4632,
        altitude_km=0, start_time_utc="2026-11-14T00:00:00Z",
        stop_time_utc="2026-11-14T00:20:00Z", step_size="10m"
    )
    assert params["COMMAND"] == "10"
    assert params["CENTER"] == "coord@301"
    assert params["SITE_COORD"].startswith("222.51000000,-89.46320000")
    assert params["QUANTITIES"] == "4"


def test_requires_explicit_east_positive_longitude_and_utc():
    with pytest.raises(ValueError):
        build_query_params(target="earth", longitude_east_deg=-137.49, latitude_deg=-89,
                           altitude_km=0, start_time_utc="2026-11-14T00:00:00Z",
                           stop_time_utc="2026-11-14T00:10:00Z")
    with pytest.raises(ValueError):
        build_query_params(target="earth", longitude_east_deg=222.51, latitude_deg=-89,
                           altitude_km=0, start_time_utc="2026-11-14T00:00:00",
                           stop_time_utc="2026-11-14T00:10:00Z")


def test_signed_east_longitude_normalisation():
    assert signed_east_to_0_360(-137.49) == pytest.approx(222.51)
    assert signed_east_to_0_360(360) == 0
