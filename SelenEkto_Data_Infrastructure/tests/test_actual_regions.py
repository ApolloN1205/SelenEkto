from pathlib import Path
import json
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from selenekto_v2.actual_regions import (SUFFIX, find_rasters, profile_region, regenerate,
                                           refresh_saved_candidates, source_regions)


def make_region(root, code='Site04', missing=()):
    folder=root/'data/raw/lola'/code
    folder.mkdir(parents=True)
    values={
      'elevation':[[1,3],[5,7]],
      'slope':[[10,20],[30,40]],
      'elevation_uncertainty':[[.1,.2],[.3,.4]],
      'slope_uncertainty':[[1,2],[3,4]],
      'measurement_count':[[0,1],[2,3]],
    }
    for layer,suffix in SUFFIX.items():
        if layer in missing:continue
        path=folder/f'{code}_final_adj_5mpp_{suffix}.tif'
        with rasterio.open(path,'w',driver='GTiff',width=2,height=2,count=1,dtype='float32',
           crs='+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m +no_defs',
           transform=from_origin(0,10,5,5),nodata=-9999) as ds:
            ds.write(np.array(values[layer],dtype='float32'),1)
    return folder


def test_real_five_layers(tmp_path):
    make_region(tmp_path)
    p=profile_region(tmp_path/'data/raw/lola','Site04','Shackleton Rim')
    assert p['availability']=='ready'
    assert p['grid']['all_five_layers_match']
    assert p['layers']['slope']['statistics']['mean']==25
    assert p['readable_metrics']['slope']['mean']==25
    assert p['readable_metrics']['elevation']['minimum']==1
    assert p['readable_metrics']['measurement_count']['pixels_with_at_least_one_spot_percent']==75


def test_missing_file_is_not_faked(tmp_path):
    make_region(tmp_path,missing=['slope'])
    p=profile_region(tmp_path/'data/raw/lola','Site04')
    assert p['availability']=='incomplete'
    assert p['readable_metrics']['slope']['mean'] is None
    assert p['layers']['slope']['status']=='missing_file'


def test_profiles_are_written_and_comparable(tmp_path):
    make_region(tmp_path)
    out=tmp_path/'data/catalog/region_profiles'
    rows=regenerate(tmp_path/'data/raw/lola',out,{'Site04':'Rim'})
    assert len(rows)==1
    assert rows[0]['mean_slope_deg']==25
    assert json.loads((out/'Site04_terrain_profile.json').read_text())['layers']['slope']['statistics']['maximum']==40
    assert (out/'regions_comparable.csv').is_file()


def test_discover_nested_download_location(tmp_path):
    folder=make_region(tmp_path)
    target=tmp_path/'data/raw/lola'
    new=target/'downloads'/'Site04';new.parent.mkdir(parents=True)
    folder.rename(new)
    assert find_rasters(target,'Site04')['slope']==new/'Site04_final_adj_5mpp_slp.tif'
    assert 'Site04' in source_regions(target)


def test_refresh_candidate_cells(tmp_path, monkeypatch):
    make_region(tmp_path)
    from selenekto_v2.core import save_candidates,load_candidates
    save_candidates(tmp_path,[{'name':'Ridge Alpha','region':'Site04','row':0,'col':1,'slope_deg':None}])
    r=refresh_saved_candidates(tmp_path)
    assert r['updated']==1
    c=load_candidates(tmp_path)[0]
    assert c['slope_deg']==20
    assert c['elevation_m']==3
    assert c['elevation_rms_m']==pytest.approx(.2)
    assert c['slope_rms_deg']==2
    assert c['lola_spot_count']==1
    assert (tmp_path/'data/catalog/named_candidates.before_raster_refresh.json').is_file()
