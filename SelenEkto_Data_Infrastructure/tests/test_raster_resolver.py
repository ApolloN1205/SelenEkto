from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from selenekto_v2.raster_resolver import resolve_region, inventory

def test_five_standard(tmp_path):
  region=tmp_path/'Site04';region.mkdir()
  for code in ('surf','slp','toterr','slperr','ldec'):
    (region/f'Site04_final_adj_5mpp_{code}.tif').touch()
  found, issues=resolve_region(tmp_path,'Site04')
  assert all(found.values()) and not issues

def test_nested_case_different(tmp_path):
  region=tmp_path/'LM1'/'another_folder';region.mkdir(parents=True)
  (region/'lm1_final_adj_5mpp_slp.TIF').touch()
  found,_=resolve_region(tmp_path,'LM1')
  assert found['slope'].name.endswith('.TIF')

def test_no_fabrication_from_other_regions(tmp_path):
  (tmp_path/'Site01').mkdir();(tmp_path/'Site04').mkdir()
  (tmp_path/'Site01'/'Site01_final_adj_5mpp_surf.tif').touch()
  found,_=resolve_region(tmp_path,'Site04')
  assert all(p is None for p in found.values())

def test_empty_directory_is_visible(tmp_path):
  (tmp_path/'DM1').mkdir()
  info=inventory(tmp_path,'DM1')
  assert info['folder_exists'] and info['files_on_disk']==0 and info['found_layers']==0

def test_ambiguous_no_guess(tmp_path):
  region=tmp_path/'Site04';region.mkdir()
  (region/'A_slp.tif').touch();(region/'B_slp.tif').touch()
  found,issues=resolve_region(tmp_path,'Site04')
  assert found['slope'] is None and 'ambiguous' in ' '.join(issues)
