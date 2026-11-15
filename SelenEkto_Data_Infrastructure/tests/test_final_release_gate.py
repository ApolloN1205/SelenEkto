import importlib.util
import io
import json
import sys
from pathlib import Path
import zipfile

MODULE = Path(__file__).resolve().parents[1] / 'scripts' / 'final_release_gate.py'
spec = importlib.util.spec_from_file_location('selenekto_final_gate',MODULE)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def fake_dist(root):
    dist = root / 'dist' / 'SelenEkto'
    for name in ('SelenEkto.exe', 'scripts/launch_selenekto_v2_controls.py',
                 'scripts/download_pgda_real.py', 'src/selenekto_v2/settings_store.py',
                 'src/selenekto_v2/library_view.py', 'src/selenekto_v2/offline_library.py',
                 'data/catalog/previews/Site01_slope.png',
                 'data/catalog/previews/LM8_slope.png',
                 'data/catalog/region_profiles/Site20_terrain_profile.json',
                 'data/raw/lola/Site01/unwanted.tif',
                 'scripts/old_before_fix.py',
                 'data/config/desktop_settings.json',
                 '_internal/runtime.dll',
                 '_internal/python315.dll',
                 '_internal/base_library.zip',
                 'release_manifest.json'):
        path=dist/name
        path.parent.mkdir(parents=True,exist_ok=True)
        if name.endswith('SelenEkto.exe'):content=b'MZ'+b'0'*512
        elif name.endswith('python315.dll'):content=b'MZ'+b'0'*100000
        elif name.endswith('base_library.zip'):
            buffer=io.BytesIO()
            with zipfile.ZipFile(buffer,'w') as packed:
                packed.writestr('encodings/__init__.pyc', b'fake-bytecode')
                packed.writestr('encodings/utf_8.pyc', b'fake-bytecode')
                packed.writestr('padding.bin', b'0'*70000, compress_type=zipfile.ZIP_STORED)
            content=buffer.getvalue()
        elif name.endswith('_slope.png'):content=b'\x89PNG\r\n\x1a\n'+b'PNG'
        elif name.endswith('settings_store.py'):content=b"DEFAULTS = {'default_layer': 'Slope'}\n#06070A"
        elif name.endswith('library_view.py'):content=b'REGIONS = tuple(region for region in REGIONS if region != "LM8")'
        elif name.endswith('launch_selenekto_v2_controls.py'):content=b'EXCLUDED_RELEASE_REGIONS = {"LM8", "Site20", "Site23"}'
        elif name.endswith('release_manifest.json'):content=json.dumps({'source_folder':'C:\\Users\\Norbert\\source'}).encode()
        else:content=b'test'
        path.write_bytes(content)
    return dist


def test_stage_removes_junk_and_source_paths(tmp_path):
    dist=fake_dist(tmp_path)
    destination=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,destination)
    assert not (destination/'data/raw/lola/Site01/unwanted.tif').exists()
    assert not (destination/'data/catalog/previews/LM8_slope.png').exists()
    assert not (destination/'data/catalog/region_profiles/Site20_terrain_profile.json').exists()
    assert not (destination/'data/config/desktop_settings.json').exists()
    assert not (destination/'scripts/old_before_fix.py').exists()
    assert not (destination/'release_manifest.json').read_text().find('source_folder')>=0
    result=gate.audit(destination)
    assert result['passed_static_checks'],result['errors']
    assert result['slope_preview_count']==1


def test_missing_preview_blocks(tmp_path):
    dist=fake_dist(tmp_path)
    (dist/'data/catalog/previews/Site01_slope.png').unlink()
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    assert not gate.audit(stage)['passed_static_checks']
    assert any('slope previews' in x for x in gate.audit(stage)['errors'])


def test_detects_nasa_tiff_and_private_path(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    raster=stage/'bad.tif';raster.write_bytes(b'fake')
    (stage/'note.txt').write_text(r'C:\Users\Norbert\Documents')
    errors=gate.audit(stage)['errors']
    assert any('NASA raster' in x for x in errors)
    assert any('personal directory' in x for x in errors)


def test_zip_has_no_junk_and_hash(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    zip_path=tmp_path/'release.zip'
    sha,size=gate.zip_release(stage,zip_path)
    assert len(sha)==64 and size>0
    with zipfile.ZipFile(zip_path) as archive:
        names=archive.namelist()
        assert 'SelenEkto/SelenEkto.exe' in names
        assert not any(n.endswith('.tif') for n in names)
        assert archive.testzip() is None


def test_builder_hardening_does_not_duplicate_imports(tmp_path):
    src=tmp_path/'scripts'/'build_windows_release.py'
    src.parent.mkdir(parents=True)
    src.write_text("args=['--hidden-import', 'requests']\nmanifest={'source_folder':str(root)}\n")
    gate.harden_builder(tmp_path)
    text=src.read_text()
    assert "'--hidden-import', 'urllib.request'" in text
    assert "'source_folder':str(root)" not in text
    gate.harden_builder(tmp_path)
    assert text == src.read_text()

def test_release_audit_rejects_lfs_pointer_runtime(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    (stage/'_internal'/'base_library.zip').write_text(
        'version https://git-lfs.github.com/spec/v1\n'
        'oid sha256:' + '0'*64 + '\n'
        'size 1425082\n'
    )
    errors=gate.audit(stage)['errors']
    assert any('base_library.zip' in x for x in errors),errors
    try:
        gate.zip_release(stage,tmp_path/'should_not_ship.zip')
    except RuntimeError as exc:
        assert 'embedded Python runtime' in str(exc)
    else:
        raise AssertionError('Packaging must fail for LFS pointer runtime')


def test_release_audit_rejects_missing_encodings(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    path=stage/'_internal'/'base_library.zip'
    with zipfile.ZipFile(path,'w') as packed:
        packed.writestr('unrelated.bin', b'0'*70000,compress_type=zipfile.ZIP_STORED)
    errors=gate.audit(stage)['errors']
    assert any('encodings' in x for x in errors),errors


def test_release_audit_rejects_missing_python_dll(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    (stage/'_internal'/'python315.dll').unlink()
    errors=gate.audit(stage)['errors']
    assert any('Python DLL' in x for x in errors),errors


def test_release_audit_accepts_verified_python_runtime(tmp_path):
    dist=fake_dist(tmp_path)
    stage=tmp_path/'stage'/'SelenEkto'
    gate.copy_portable(dist,stage)
    errors=gate.embedded_python_errors(stage)
    assert errors == []
