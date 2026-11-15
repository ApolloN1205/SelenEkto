import ast
import importlib.util
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]

def load(name,source):
    spec=importlib.util.spec_from_file_location(name,source)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

patch=load('patch_clean_install', BASE/'scripts'/'apply_clean_install_repair.py')
entry=load('selenekto_entry_repaired', BASE/'release'/'selenekto_entry.py')
checker=load('portable_release_checker', BASE/'scripts'/'check_portable_release.py')


def test_startup_report_exists_and_does_not_need_qt(tmp_path,monkeypatch):
    monkeypatch.setattr(entry,'application_root',lambda:tmp_path)
    exc=RuntimeError('broken scientific dependency')
    path=entry.log_failure(exc)
    assert path and path.is_file()
    assert 'broken scientific dependency' in path.read_text(encoding='utf-8')


def test_patcher_idempotent_on_supported_launch_source():
    source=(Path('/mnt/data/SelenEkto_Illumination_Branding_Repair/scripts/launch_selenekto_v2_controls.py'))
    if not source.is_file():
        return
    original=source.read_text(encoding='utf-8')
    modified=patch.patch_launcher(original)
    ast.parse(modified)
    assert 'Offline slope previews' not in original
    assert 'Open Data Library' in modified
    assert patch.patch_launcher(modified)==modified


def test_portable_check_rejects_missing_assets(tmp_path):
    (tmp_path/'SelenEkto.exe').write_bytes(b'exe')
    result=checker.inspect_release(tmp_path)
    assert result['portable_ready_for_smoke_test'] is False
    assert 'src/selenekto_v2/offline_library.py' in result['missing_required']


def test_portable_check_accepts_compact_data(tmp_path):
    for name in ('SelenEkto.exe','scripts/launch_selenekto_v2_controls.py','src/selenekto_v2/library_view.py','src/selenekto_v2/offline_library.py','data/catalog/previews/Site01_slope.png'):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'content')
    result=checker.inspect_release(tmp_path)
    assert result['portable_ready_for_smoke_test']
    assert result['slope_previews']==1
