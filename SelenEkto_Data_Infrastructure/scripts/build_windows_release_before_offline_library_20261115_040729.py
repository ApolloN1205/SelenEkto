"""Build a portable, no-terminal SelenEkto Windows directory using PyInstaller."""
from __future__ import annotations
import argparse
import os
import shutil
import subprocess
import sys
import json
from pathlib import Path


def build(root: Path, dry_run: bool = False) -> list[str]:
    root = root.resolve()
    if os.name != 'nt':
        raise RuntimeError('Build the Windows executable on Windows, using the project venv.')
    launcher = root / 'scripts' / 'launch_selenekto_v2_controls.py'
    if not launcher.is_file():
        raise FileNotFoundError(f'Missing current launcher: {launcher}')
    entry = root / 'release' / 'selenekto_entry.py'
    if not entry.is_file():
        raise FileNotFoundError(f'Missing release entrypoint: {entry}')
    dest = root / 'dist' / 'SelenEkto'
    if dest.exists():
        raise FileExistsError('Existing dist/SelenEkto detected; move it aside manually before rebuilding: ' + str(dest))
    icon = root / 'assets' / 'branding' / 'logo.ico'
    args = [sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
            '--onedir', '--windowed', '--name', 'SelenEkto',
            '--distpath', str(root/'dist'), '--workpath', str(root/'build'/'pyinstaller'),
            '--specpath', str(root/'build'), '--paths', str(root/'src'),
            '--collect-submodules', 'selenekto_v2', '--collect-submodules', 'selenekto_data',
            '--collect-all', 'rasterio', '--collect-all', 'pyproj',
            '--hidden-import', 'PySide6.QtSvg',
            '--hidden-import', 'matplotlib.backends.backend_qtagg',
            '--hidden-import', 'PIL.Image',
            '--hidden-import', 'requests']
    if icon.exists():
        args += ['--icon', str(icon)]
    args += [str(entry)]
    print('Build command:',' '.join(args))
    if dry_run:
        return args
    subprocess.run(args, cwd=root, check=True)
    # Python files remain beside executable: the existing app assumes project-root paths.
    shutil.copytree(root/'scripts', dest/'scripts', ignore=shutil.ignore_patterns('__pycache__','*.pyc','*_backup*.py','*_pre_*.py','*_before_*.py','*_pre_*.py','*.bak','*_old.py'), dirs_exist_ok=True)
    shutil.copytree(root/'src', dest/'src', ignore=shutil.ignore_patterns('__pycache__','*.pyc'), dirs_exist_ok=True)
    assets = root/'assets'
    if assets.is_dir():
        shutil.copytree(assets, dest/'assets', dirs_exist_ok=True)
    profiles = root/'data'/'catalog'/'region_profiles'
    if profiles.is_dir():
        shutil.copytree(profiles, dest/'data'/'catalog'/'region_profiles',dirs_exist_ok=True)
    (dest/'data'/'raw'/'lola').mkdir(parents=True,exist_ok=True)
    (dest/'data'/'processed'/'logs').mkdir(parents=True,exist_ok=True)
    (dest/'data'/'config').mkdir(parents=True,exist_ok=True)
    # Add original source licences and compact manifests when available.
    for name in ('README.md','LICENSE','LICENSE.txt','pyproject.toml'):
        if (root/name).is_file(): shutil.copy2(root/name,dest/name)
    (dest/'README_START_HERE.txt').write_text(
        'SelenEkto portable Windows application\n\n'
        'Double-click SelenEkto.exe. No PowerShell or Git required.\n'
        'Terrain statistics work only where processed profiles exist.\n'
        'Full-resolution per-pixel analysis requires NASA GeoTIFFs in data/raw/lola/<region>/.\n'
        'Place the portable folder somewhere writable (for example Documents), not Program Files.\n'
        'This build excludes large raw TIFFs by design.\n'
        'If the app fails, inspect data/processed/logs/release_startup_error.log.\n',encoding='utf-8')
    (dest/'release_manifest.json').write_text(json.dumps({
        'app':'SelenEkto','format':'portable-windows-onedir','raw_rasters_included':False,
        'source_folder':str(root),'scientific_validation':'not independently certified'
    }, indent=2),encoding='utf-8')
    print('Portable directory:',dest)
    print('Smoke test required: double-click executable and verify Explorer, Compare, Illumination, Settings.')
    return args


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    build(args.root, dry_run=args.dry_run)


if __name__ == '__main__':
    main()
