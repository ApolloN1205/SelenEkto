import json
from pathlib import Path
from selenekto_v2.neon_solar import parse_saved_result

def test_solar_colors(tmp_path):
    p=tmp_path/'s.json';p.write_text(json.dumps({'records':[{'timestamp_utc':'2026-01-01T00:00:00Z','altitude_deg':2,'baseline_horizon_deg':1,'low_scenario_horizon_deg':0,'high_scenario_horizon_deg':2}]}))
    d=parse_saved_result(p)
    assert d['kind']=='solar' and d['lines'][0]['color']=='#FFE347'

def test_horizon(tmp_path):
    p=tmp_path/'h.json';p.write_text(json.dumps({'site':'Site04','angles':[{'grid_azimuth_deg':0,'horizon_angle_deg':3}]}))
    assert parse_saved_result(p)['lines'][0]['values']==[3]

def test_bad_json(tmp_path):
    import pytest
    p=tmp_path/'bad.json';p.write_text('{}')
    with pytest.raises(ValueError):parse_saved_result(p)
