from pathlib import Path
import json
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from selenekto_v2.core import region_names,region_files,region_health,normalize_record,validate_name,load_candidates,save_candidates,comparable

def test_name_validation():
    assert validate_name('  Peak   A  ')=='Peak A'
    for value in ('', '@SUM(1)', 'a'*65):
        with pytest.raises(ValueError):validate_name(value)

def test_region_paths(tmp_path):
    p=region_files(tmp_path,'Site04')
    assert p['Slope'].name=='Site04_final_adj_5mpp_slp.tif'
    with pytest.raises(ValueError):region_files(tmp_path,'../Site01')

def test_discovery_and_missing_health(tmp_path):
    target=tmp_path/'data/catalog/region_profiles';target.mkdir(parents=True)
    (target/'Site01_terrain_profile.json').write_text('{}')
    assert region_names(tmp_path)==['Site01']
    health=region_health(tmp_path,'Site01')
    assert health['status']=='incomplete'
    assert len(health['missing'])==5

def test_candidates_roundtrip(tmp_path):
    record={'name':'Ridge Alpha','region':'Site01','row':10,'col':20,'elevation_m':0,
            'slope_deg':2.5,'lola_spot_count':0,'elevation_rms_m':None}
    path=save_candidates(tmp_path,[record]);assert path.exists()
    loaded=load_candidates(tmp_path)
    assert loaded[0]['name']=='Ridge Alpha'
    assert loaded[0]['elevation_m']==0
    assert loaded[0]['lola_spot_count']==0
    assert loaded[0]['elevation_rms_m'] is None

def test_comparison_rejects_insufficient_or_duplicates():
    records=[{'name':'A'},{'name':'B'},{'name':'C'}]
    assert len(comparable(records,[0,2]))==2
    for indices in ([0],[0,0],[0,4]):
        with pytest.raises(ValueError):comparable(records,indices)

def test_normalize_rejects_malicious_name():
    with pytest.raises(ValueError):normalize_record({'name':'=1+1','region':'Site01','row':0,'col':0})

def test_health_aligns_synthetic_rasters(tmp_path):
    import rasterio
    import numpy as np
    from rasterio.transform import from_origin
    paths=region_files(tmp_path,'Site01')
    for path in paths.values():
        path.parent.mkdir(parents=True,exist_ok=True)
        with rasterio.open(path,'w',driver='GTiff',width=5,height=5,count=1,dtype='float32',
                             crs='+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m',transform=from_origin(0,25,5,5)) as ds:
            ds.write(np.ones((5,5),dtype='float32'),1)
    assert region_health(tmp_path,'Site01')['status']=='ready'
    from selenekto_v2.core import read_cell
    r=read_cell(tmp_path,'Site01',2,3)
    assert r['slope_deg']==1.0
    assert r['x_projected_m']==17.5
