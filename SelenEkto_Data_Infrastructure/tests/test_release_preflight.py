import importlib.util
from pathlib import Path

p = Path(__file__).resolve().parents[1] / 'scripts' / 'release_preflight.py'
spec=importlib.util.spec_from_file_location('release_preflight',p)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

def test_empty_regions_are_not_called_complete(tmp_path):
    region=m.inspect_region(tmp_path,'LM8')
    assert region['files_found']==0
    assert region['presence_status']=='incomplete'

def test_file_presence_is_not_claimed_validity(tmp_path):
    directory=tmp_path/'data'/'raw'/'lola'/'Site01'
    directory.mkdir(parents=True)
    for suffix in m.LAYER_SUFFIXES:
        (directory / f'Site01_final_adj_5mpp_{suffix}.tif').write_bytes(b'not a raster')
    region=m.inspect_region(tmp_path,'Site01')
    assert region['files_found']==5
    assert 'does not validate' in region['note']

def test_preflight_does_not_modify(tmp_path):
    before=set(tmp_path.rglob('*'))
    data=m.audit(tmp_path)
    assert data['summary']['regions_with_five_files']==0
    assert set(tmp_path.rglob('*')) == before

def test_names_and_count():
    assert len(m.REGION_CODES)==27
    assert len(set(m.REGION_CODES))==27
    assert len(m.LAYER_SUFFIXES)==5
