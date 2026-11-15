import importlib.util
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

MODULE=Path(__file__).resolve().parents[1]/'scripts'/'validate_raster_alignment.py'
spec=importlib.util.spec_from_file_location('selenekto_raster_screen',MODULE)
validator=importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def make_set(tmp_path, slope_transform=None, slope_value=10):
    folder=tmp_path/'data'/'raw'/'lola'/'Site01'
    folder.mkdir(parents=True)
    for name,suffix in validator.LAYER_CODES.items():
        transform=(slope_transform if suffix=='slp' and slope_transform else from_origin(0,10,1,1))
        val=slope_value if suffix=='slp' else 3
        with rasterio.open(folder/f'Site01_final_adj_5mpp_{suffix}.tif','w',driver='GTiff',
                           height=10,width=10,count=1,dtype='float32',transform=transform,crs='EPSG:4326') as ds:
            ds.write(np.full((10,10),val,dtype='float32'),1)


def test_valid_grid_sample(tmp_path,monkeypatch):
    make_set(tmp_path)
    monkeypatch.setattr(validator,'REGIONS',('Site01',))
    result=validator.validate(tmp_path)
    assert result['all_included_complete_and_grid_aligned']


def test_misaligned_slope_rejected(tmp_path,monkeypatch):
    make_set(tmp_path,slope_transform=from_origin(2,10,1,1))
    monkeypatch.setattr(validator,'REGIONS',('Site01',))
    result=validator.validate(tmp_path)
    assert not result['all_included_complete_and_grid_aligned']
    assert result['results'][0]['status']=='invalid_or_misaligned'


def test_invalid_slope_rejected(tmp_path,monkeypatch):
    make_set(tmp_path,slope_value=105)
    monkeypatch.setattr(validator,'REGIONS',('Site01',))
    result=validator.validate(tmp_path)
    assert not result['all_included_complete_and_grid_aligned']
    assert any('0–90' in x for x in result['results'][0]['issues'])
