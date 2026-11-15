from pathlib import Path
import ast
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def test_launcher_compiles_and_has_app_branding():
    source=(ROOT/'scripts/launch_selenekto_v2_controls.py').read_text()
    ast.parse(source)
    assert 'SelenEkto.LunarNavigator.Desktop.v2' in source
    assert 'setApplicationDisplayName' in source
    assert "assets/branding/logo.png" in source


def test_horizon_calculates_from_candidate_region_not_site01():
    from selenekto_v2.illumination_controls import calculate_candidate_horizon
    source=__import__('inspect').getsource(calculate_candidate_horizon)
    assert "region=str(candidate['region'])" in source
    assert 'region_files(root,region)' in source
    assert "paths=region_files(root,region)" in source


def test_error_explanation_includes_missing_data():
    from selenekto_v2.illumination_controls import explain_error
    assert 'NASA data is missing' in explain_error(FileNotFoundError('missing raster'))


def test_offline_horizon_uses_real_selected_region(tmp_path, monkeypatch):
    import types
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from selenekto_v2.illumination_controls import calculate_candidate_horizon
    import sys
    region='Site07'
    folder=tmp_path/'data/raw/lola'/region
    folder.mkdir(parents=True)
    paths={}
    for label, suffix, value in [('Elevation','surf',100.0),('LOLA observations','ldec',2.0),
                                 ('Elevation uncertainty','toterr',0.2)]:
        path=folder/f'{region}_final_adj_5mpp_{suffix}.tif'
        with rasterio.open(path,'w',driver='GTiff',width=80,height=80,count=1,dtype='float32',
                           crs='+proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400 +units=m',
                           transform=from_origin(-200,200,5,5)) as ds:
            ds.write(np.full((80,80),value,dtype=np.float32),1)
        paths[label]=path
    import pytest
    core=pytest.importorskip("selenekto_v2.core")
    monkeypatch.setattr(core,'region_health',lambda root,r: {'status':'ready','details':'ready'})
    monkeypatch.setattr(core,'region_files',lambda root,r: paths)
    result,path=calculate_candidate_horizon(tmp_path,{'name':'Test ridge','region':region,'row':40,'col':40},scan_m=40)
    assert result['candidate']['region']=='Site07'
    assert len(result['angles'])==360
    assert path.is_file()
    assert 'Site07' in str(path)
