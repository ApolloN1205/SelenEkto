import json
from pathlib import Path
import numpy as np
import rasterio
from rasterio.transform import from_origin
from selenekto_data.region_profiles import LAYERS, inspect_region, generate_catalogue


def make_region(root, name='Site01', missing=None, nodata=False, mismatched=False):
    folder=root/name;folder.mkdir(parents=True,exist_ok=True)
    for key,(suffix,_unit) in LAYERS.items():
        if key==missing:continue
        data=np.full((6,6),3.5,dtype='float32')
        if key=='measurement_count':data[:]=0;data[2,2]=2
        if nodata and key=='slope':data[:]=np.nan
        transform=from_origin(0,40,6 if mismatched and key=='slope' else 5,5)
        with rasterio.open(folder/f'{name}_final_adj_5mpp_{suffix}.tif','w',driver='GTiff',
                            width=6,height=6,count=1,dtype='float32',crs='EPSG:3857',
                            transform=transform,nodata=np.nan) as ds:ds.write(data,1)


def test_ready(tmp_path):
    make_region(tmp_path)
    d=inspect_region(tmp_path,'Site01','Example')
    assert d['availability']=='ready'
    assert d['grid']['all_five_layers_match']
    assert d['layers']['slope']['statistics']['valid_pixels']==36
    assert d['layers']['measurement_count']['statistics']['pixels_with_at_least_one_spot']==1


def test_missing(tmp_path):
    make_region(tmp_path,missing='slope')
    d=inspect_region(tmp_path,'Site01')
    assert d['availability']=='incomplete'
    assert d['layers']['slope']['status']=='missing_file'


def test_grid_mismatch(tmp_path):
    make_region(tmp_path,mismatched=True)
    assert inspect_region(tmp_path,'Site01')['availability']=='invalid_or_misaligned'


def test_nodata(tmp_path):
    make_region(tmp_path,nodata=True)
    d=inspect_region(tmp_path,'Site01')
    assert d['layers']['slope']['statistics']['valid_pixels']==0
    assert d['availability']=='contains_all_nodata_layer'


def test_json_for_missing_region(tmp_path):
    output=tmp_path/'json'
    rows=list(generate_catalogue(tmp_path/'raw',output,{'Site01':'One','Site04':'Four'}))
    assert len(rows)==2
    assert json.loads((output/'regions_index.json').read_text())['total_regions']==2
    assert (output/'Site04_terrain_profile.json').is_file()
