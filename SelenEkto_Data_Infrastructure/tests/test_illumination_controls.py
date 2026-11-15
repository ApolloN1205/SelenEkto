from datetime import datetime,timezone
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from selenekto_v2.illumination_controls import validate_timeline, explain_error


def test_valid_date_and_hours():
    d,h,s=validate_timeline(datetime(2026,11,15,4,30,tzinfo=timezone.utc),72,60)
    assert (h,s,d.hour)==(72,60,4)

@pytest.mark.parametrize('hours,step',[(0,60),(337,60),(72,9),(72,721)])
def test_bad_ranges(hours,step):
    with pytest.raises(ValueError):validate_timeline(datetime.now(timezone.utc),hours,step)

def test_naive_datetime_not_accepted():
    with pytest.raises(ValueError,match='UTC'):
        validate_timeline(datetime(2026,11,15),72,60)

def test_missing_raster_error_is_clear():
    msg=explain_error(FileNotFoundError('Missing terrain raster'))
    assert 'NASA data is missing' in msg

def test_network_error_is_clear():
    msg=explain_error(OSError('urlopen error network unreachable'))
    assert 'JPL Horizons' in msg

def test_deprecation_not_needed():
    assert 'No solar values were generated' in explain_error(OSError('urlopen error refused'))

def test_candidate_analysis_uses_own_region(tmp_path,monkeypatch):
    """End-to-end local GeoTIFF calculation with a mocked Horizons API (offline)."""
    import numpy as np, rasterio, types
    from rasterio.transform import from_origin
    import selenekto_data.candidate_solar as candidate_solar
    import selenekto_data.solar as solar
    from selenekto_v2 import illumination_controls as ctl
    import sys

    region='Site04';base=tmp_path/'data/raw/lola'/region;base.mkdir(parents=True)
    paths={}
    for label,code,value in [('Elevation','surf',100.0),('LOLA observations','ldec',2.0),('Elevation uncertainty','toterr',.2)]:
        path=base/(f'{region}_final_adj_5mpp_{code}.tif');paths[label]=path
        with rasterio.open(path,'w',driver='GTiff',height=100,width=100,count=1,dtype='float32',
                  transform=from_origin(-250,250,5,5),crs='+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs') as ds:
            ds.write(np.full((100,100),value,dtype='float32'),1)
    core=types.ModuleType('selenekto_v2.core')
    core.region_health=lambda root,region:{'status':'ready','details':'5 files checked'}
    core.region_files=lambda root,region:paths
    monkeypatch.setitem(sys.modules,'selenekto_v2.core',core)
    monkeypatch.setattr(candidate_solar,'candidate_geography',lambda *args:(-89.5,-137.0))
    monkeypatch.setattr(solar,'project_north_offset',lambda *args:0.0)
    queried=[]
    def fake_sun(lat,lon,elev,start,hours,interval):
        queried.append((lat,lon,elev,hours,interval))
        return ([{'timestamp_utc':'2026-11-15T00:00:00Z','north_azimuth_deg':0,'altitude_deg':20.0}],{'provider':'offline test'})
    monkeypatch.setattr(candidate_solar,'fetch_candidate_sun',fake_sun)
    result,file=ctl.calculate_candidate_timeline(tmp_path,{'region':region,'name':'Alpha','row':50,'col':50},
             datetime(2026,11,15,tzinfo=timezone.utc),24,60,scan_m=40)
    assert queried==[(-89.5,-137.0,100.0,24,60)]
    assert result['candidate']['region']=='Site04'
    assert result['summary']['sample_count']==1
    assert file.is_file()
    assert 'Site04' in str(file)


def test_partial_boundary_horizon_is_not_presented_as_complete(tmp_path, monkeypatch):
    """A 360-azimuth result may still have incomplete distance coverage."""
    import numpy as np
    import rasterio
    import sys
    import types
    from rasterio.transform import from_origin
    from selenekto_v2 import illumination_controls as ctl
    import selenekto_data.horizon as horizon_module
    from selenekto_data import candidate_solar

    region = 'Site04'
    raster = tmp_path / 'dem.tif'
    with rasterio.open(raster, 'w', driver='GTiff', height=20, width=20,
                       count=1, dtype='float32',
                       transform=from_origin(-50, 50, 5, 5),
                       crs='+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m +no_defs') as ds:
        ds.write(np.full((20, 20), 100.0, dtype='float32'), 1)
    paths = {'Elevation': raster, 'LOLA observations': raster,
             'Elevation uncertainty': raster}
    core = types.ModuleType('selenekto_v2.core')
    core.region_health = lambda root, key: {'status': 'ready', 'details': 'test'}
    core.region_files = lambda root, key: paths
    monkeypatch.setitem(sys.modules, 'selenekto_v2.core', core)

    candidate = {'region': region, 'name': 'Edge', 'row': 10, 'col': 10}
    # A 120 m scan exceeds the 100 m-wide raster in every direction.
    with pytest.raises(ValueError, match='DEM ends before the requested scan radius'):
        ctl.calculate_candidate_horizon(tmp_path, candidate, scan_m=120)

    def forbidden_network(*args, **kwargs):
        raise AssertionError('Do not query JPL when the horizon is incomplete')
    monkeypatch.setattr(candidate_solar, 'fetch_candidate_sun', forbidden_network)
    with pytest.raises(ValueError, match='DEM ends before the requested scan radius'):
        ctl.calculate_candidate_timeline(
            tmp_path, candidate, datetime(2026, 11, 15, tzinfo=timezone.utc),
            24, 60, scan_m=120)
