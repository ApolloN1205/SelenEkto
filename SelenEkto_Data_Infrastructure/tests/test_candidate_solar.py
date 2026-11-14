import pytest
from selenekto_data.candidate_solar import evaluate_candidate,timeline_statistics,normalized_scores,fetch_candidate_sun
from datetime import datetime,timezone
import json


def horizon(degrees):
    return [{'grid_azimuth_deg':i,'horizon_angle_deg':degrees} for i in range(360)]


def test_candidate_independent_horizon():
    sun=[{'timestamp_utc':'2026-11-14T00:00:00Z','north_azimuth_deg':12.,'altitude_deg':2.}]
    clear=evaluate_candidate(sun,horizon(1),0)
    blocked=evaluate_candidate(sun,horizon(3),0)
    assert clear[0]['sun_centre_clear_baseline'] is True
    assert blocked[0]['sun_centre_clear_baseline'] is False
    assert timeline_statistics(clear)['clear_sample_fraction']==1


def test_grid_orientation_offset():
    sun=[{'timestamp_utc':'2026-11-14T00:00:00Z','north_azimuth_deg':10.,'altitude_deg':0.}]
    r=evaluate_candidate(sun,horizon(-1),45)
    assert r[0]['grid_azimuth_deg']==55


def test_scoring_preference_change():
    rows=[{'name':'A','clear_sample_fraction':.8,'slope_deg':10,'elevation_rms_m':.5},
          {'name':'B','clear_sample_fraction':.3,'slope_deg':2,'elevation_rms_m':.1}]
    a=normalized_scores(rows,{'clear_sample_fraction':10,'slope_deg':1,'elevation_rms_m':1})
    b=normalized_scores(rows,{'clear_sample_fraction':1,'slope_deg':10,'elevation_rms_m':1})
    assert a[0]['weighted_score']>a[1]['weighted_score']
    assert b[1]['weighted_score']>b[0]['weighted_score']


def test_incomplete_horizon_rejected():
    with pytest.raises(ValueError):
        evaluate_candidate([{'north_azimuth_deg':0,'altitude_deg':3}],[],0)


def test_zero_weights_rejected():
    with pytest.raises(ValueError):
        normalized_scores([{'clear_sample_fraction':.5,'slope_deg':3,'elevation_rms_m':.1}],{'clear_sample_fraction':0,'slope_deg':0,'elevation_rms_m':0})


def test_horizons_request_uses_candidate_coords():
    def fake_transport(url):
        from urllib.parse import urlparse,parse_qs
        q=parse_qs(urlparse(url).query)
        assert '12.50000000' in q['SITE_COORD'][0] and '-89.50000000' in q['SITE_COORD'][0]
        return json.dumps({'result':'$$SOE\n2026-Nov-14 00:00, 180.0, -2.0\n$$EOE'})
    positions, metadata=fetch_candidate_sun(-89.5,12.5,1000,datetime(2026,11,14,tzinfo=timezone.utc),24,60,transport=fake_transport)
    assert positions[0]['altitude_deg']==-2
    assert metadata['provider']=='NASA/JPL Horizons'
