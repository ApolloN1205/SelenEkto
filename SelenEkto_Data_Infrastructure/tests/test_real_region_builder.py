import importlib.util
import json
import sys
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]

def test_real_raster_values_and_missing_layers(tmp_path):
    rasterio=pytest.importorskip('rasterio')
    # Import the shipped builder exactly as a user would after the full add-on is installed.
    script=ROOT/'scripts/rebuild_real_region_profiles.py'
    spec=importlib.util.spec_from_file_location('selenekto_real_regions_script',script)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    raw=tmp_path/'data/raw/lola';region='Site01';regdir=raw/region;regdir.mkdir(parents=True)
    from rasterio.transform import from_origin
    for suffix,datum in [('surf',12),('ldec',2),('toterr',.2),('slp',8),('slperr',1)]:
        with rasterio.open(regdir/f'{region}_final_adj_5mpp_{suffix}.tif','w',driver='GTiff',width=2,height=2,count=1,
                           dtype='float32',crs='+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m +type=crs',
                           transform=from_origin(0,0,5,5)) as dst:
            dst.write(np.full((2,2),datum,dtype='float32'),1)
    output=tmp_path/'data/catalog/region_profiles'
    rows=module.rebuild(raw,output,{'Site01':'Connecting ridge','Site04':'Shackleton rim'})
    assert rows[0]['status']=='ready' and rows[1]['status']=='incomplete'
    valid=json.loads((output/'Site01_terrain_profile.json').read_text())
    assert valid['layers']['slope']['statistics']['mean']==8.0
    assert valid['readable_metrics']['slope']['mean']==8.0
    assert valid['grid']['all_five_layers_match']
    missing=json.loads((output/'Site04_terrain_profile.json').read_text())
    assert missing['availability']=='incomplete'
    assert missing['readable_metrics']['slope']['mean'] is None
