import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_final_consolidation import change_launcher,change_library,change_settings,change_builder,TAG

def test_launcher_filters_without_editing_candidate_store():
    source='from selenekto_v2.region_data import load_profiles, METRIC_COLUMNS, metric_value\n'
    patched=change_launcher(source)
    assert 'LM8' in patched and 'Site20' in patched and 'Site23' in patched
    assert 'save_candidates' not in patched
    assert change_launcher(patched)==patched

def test_library_filters():
    line='from .offline_library import REGIONS,LAYERS,KNOWN_ISSUES,catalogue_status,preview_path,generate_preview\n'
    patched=change_library(line)
    assert 'REGIONS = tuple(' in patched
    assert change_library(patched)==patched

def test_obsidian_specific_override():
    line="    style += f'''\\nQMainWindow,QWidget {{font-size:{s['font_size']}px;}}"
    patched=change_settings(line)
    assert "s['theme'] == 'Obsidian'" in patched
    assert '#06070A' in patched
    assert change_settings(patched)==patched

def test_builder_removes_only_distribution_copies():
    patched=change_builder("    print('Portable directory:',dest)\n")
    assert 'for region in' in patched and "folder = dest/subfolder" in patched
    assert change_builder(patched)==patched
