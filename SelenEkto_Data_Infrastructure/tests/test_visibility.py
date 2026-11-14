from selenekto_data.visibility import cyclic_interpolate, classify_sky_position, evaluate_csv, read_site_results
import json
import pytest

def test_wrap_interpolation():
    points=[(0,0),(90,9),(180,18),(270,27)]
    assert cyclic_interpolate(points,45)==pytest.approx(4.5)
    assert cyclic_interpolate(points,315)==pytest.approx(13.5)
    assert cyclic_interpolate(points,-45)==pytest.approx(13.5)

def test_visibility_with_scenarios():
    p=[(0,1),(180,1)]
    u=[(0,0,2),(180,0,2)]
    assert 'ABOVE' in classify_sky_position(p,u,0,3)['status']
    assert 'BELOW' in classify_sky_position(p,u,0,-1)['status']
    assert 'SCENARIO-DEPENDENT' in classify_sky_position(p,u,0,1)['status']

def test_invalid_altitude():
    with pytest.raises(ValueError):classify_sky_position([(0,0),(180,0)],None,0,91)

def test_csv_evaluation(tmp_path):
    f=tmp_path/'sky.csv'
    f.write_text('timestamp_utc,grid_azimuth_deg,altitude_deg\n2026-11-14T00:00:00Z,0,2\n',encoding='utf8')
    r=evaluate_csv(f,[(0,0),(180,0)],None)
    assert len(r)==1 and 'ABOVE' in r[0]['status']

def test_read_reports_mismatch(tmp_path):
    a=tmp_path/'a.json';b=tmp_path/'b.json'
    a.write_text(json.dumps({'angles':[{'grid_azimuth_deg':0,'horizon_angle_deg':1},{'grid_azimuth_deg':180,'horizon_angle_deg':2}]}))
    b.write_text(json.dumps({'directions':[{'grid_azimuth_deg':0,'low_scenario_angle_deg':0,'high_scenario_angle_deg':2}]}))
    with pytest.raises(ValueError): read_site_results(a,b)
