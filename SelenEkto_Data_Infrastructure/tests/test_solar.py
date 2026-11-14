from datetime import datetime,timezone
import json
import pytest
from selenekto_data.solar import (parse_horizons_csv_table,horizons_parameters,fetch_sun_positions,
                                  convert_to_grid,evaluate_solar_timeline)

MOCK='''Header text\n$$SOE\n 2026-Nov-14 00:00, , , 135.10000, 1.25000,\n 2026-Nov-14 01:00, *, , 136.20000, -2.50000,\n$$EOE\nFooter'''

def test_parse():
    x=parse_horizons_csv_table(MOCK)
    assert len(x)==2 and x[0]['north_azimuth_deg']==135.1
    assert x[1]['altitude_deg']==-2.5

def test_fail_closed():
    with pytest.raises(ValueError):parse_horizons_csv_table('unrecognised')
    with pytest.raises(ValueError):parse_horizons_csv_table('$$SOE\n2026-Nov-14 00:00, 1, 2, 3\n$$EOE')

def test_params():
    p=horizons_parameters(datetime(2026,11,14,tzinfo=timezone.utc),hours=12,step_minutes=60)
    assert p['CENTER']=="'coord@301'"
    assert p['QUANTITIES']=="'4'"
    assert '1.94463257' in p['SITE_COORD']

def test_mock_fetch():
    value,meta=fetch_sun_positions(datetime(2026,11,14,tzinfo=timezone.utc), transport=lambda url:json.dumps({'result':MOCK}))
    assert len(value)==2 and meta['returned_records']==2

def test_rotate():
    out=convert_to_grid([{'north_azimuth_deg':350}],25)
    assert out[0]['grid_azimuth_deg']==15

def test_evaluation():
    horizon=[(0,1),(90,1),(180,1),(270,1)]
    points=[{'timestamp_utc':'2026-11-14T00:00:00Z','grid_azimuth_deg':0,'north_azimuth_deg':0,'altitude_deg':2}]
    rows=evaluate_solar_timeline(points,horizon,None)
    assert rows[0]['baseline_clearance_deg']==1
    assert rows[0]['status']=='ABOVE baseline horizon'

def test_projected_north_orientation_is_finite():
    from pyproj import CRS
    from selenekto_data.solar import project_north_offset
    lunar_polar = CRS.from_proj4('+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs')
    bearing = project_north_offset(lunar_polar.to_wkt())
    assert 0 <= bearing < 360
    assert bearing == pytest.approx(222.51, abs=0.01)
