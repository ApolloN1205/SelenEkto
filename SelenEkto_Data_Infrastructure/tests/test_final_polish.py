import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_project_cleanup import candidates
from report_release_size import report


def test_dry_cleanup_only_generated_files(tmp_path):
    (tmp_path/'scripts').mkdir();(tmp_path/'src').mkdir()
    (tmp_path/'scripts'/'__pycache__').mkdir()
    (tmp_path/'scripts'/'__pycache__'/'thing.pyc').write_bytes(b'abc')
    (tmp_path/'data'/'raw'/'lola').mkdir(parents=True)
    (tmp_path/'data'/'raw'/'lola'/'a.tif').write_bytes(b'abc')
    (tmp_path/'dist'/'SelenEkto').mkdir(parents=True)
    (tmp_path/'dist'/'SelenEkto'/'SelenEkto.exe').write_bytes(b'exe')
    paths=[p for p,_ in candidates(tmp_path)]
    assert paths==[tmp_path/'scripts'/'__pycache__']


def test_branding_patch_anchors():
    reference=Path('/mnt/data/SelenEkto_Settings_Upgrade/scripts/launch_selenekto_v2_settings.py')
    if reference.is_file():
        source=reference.read_text(encoding='utf-8')
        assert 'side.addWidget(img)' in source
        assert 'self.setWindowIcon(icon)' in source


def test_build_excludes_junction_data(tmp_path,capsys):
    (tmp_path/'dist'/'SelenEkto').mkdir(parents=True)
    (tmp_path/'dist'/'SelenEkto'/'SelenEkto.exe').write_bytes(b'exe')
    report(tmp_path)
    out=capsys.readouterr().out
    assert 'Bundled NASA TIFFs: 0' in out
