from selenekto_data.candidate_compare import comparison_series
import pytest


def test_comparison_retains_metric_columns():
    names, fields = comparison_series([
        {'name': 'A', 'elevation_m': 10, 'slope_deg': 7, 'elevation_rms_m': .2, 'lola_spot_count': 0},
        {'name': 'B', 'elevation_m': 12, 'slope_deg': 3, 'elevation_rms_m': .1, 'lola_spot_count': 2},
    ])
    assert names == ['A', 'B']
    assert fields['elevation_m'] == [10., 12.]
    assert fields['lola_spot_count'] == [0., 2.]


def test_missing_measurements_are_not_zero():
    _, fields = comparison_series([{'name': 'A', 'slope_deg': None}, {'name': 'B', 'slope_deg': 'nan'}])
    assert fields['slope_deg'] == [None, None]


def test_rejects_single_candidate():
    with pytest.raises(ValueError):
        comparison_series([{'name': 'Only one'}])
