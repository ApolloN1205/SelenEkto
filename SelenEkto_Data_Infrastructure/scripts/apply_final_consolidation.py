"""Final SelenEkto catalogue exclusions and Obsidian dark-mode patch.

This script never deletes or edits NASA rasters, candidate records or project data.
Safe to re-run. Stops when unsupported source layout is detected.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = frozenset({'LM8', 'Site20', 'Site23'})
TAG = 'SELENEKTO_FINAL_CONSOLIDATION_V1'


def change_launcher(source: str) -> str:
    if TAG in source:
        return source
    marker = 'from selenekto_v2.region_data import load_profiles, METRIC_COLUMNS, metric_value'
    if source.count(marker) != 1:
        raise ValueError('Cannot find expected region profile import in launcher; launcher not changed')
    # Keep all stored candidates intact; this only filters displayed region catalogues.
    extra = '''\n# SELENEKTO_FINAL_CONSOLIDATION_V1 — Hide 3 unreliable catalogued regions, preserve all underlying data.\nEXCLUDED_RELEASE_REGIONS = frozenset({'LM8', 'Site20', 'Site23'})\n_original_region_names = region_names\ndef region_names(root):\n    return [name for name in _original_region_names(root) if name not in EXCLUDED_RELEASE_REGIONS]\n_original_load_profiles = load_profiles\ndef load_profiles(folder):\n    return [p for p in _original_load_profiles(folder)\n            if p.get('site_code') not in EXCLUDED_RELEASE_REGIONS]\n'''
    return source.replace(marker, marker + extra, 1)


def change_library(source: str) -> str:
    if TAG in source:
        return source
    marker = 'from .offline_library import REGIONS,LAYERS,KNOWN_ISSUES,catalogue_status,preview_path,generate_preview'
    if source.count(marker) != 1:
        raise ValueError('Cannot locate Data Library imports; library not changed')
    source = source.replace(marker, marker + "\n# " + TAG + "\nREGIONS = tuple(region for region in REGIONS if region not in {'LM8', 'Site20', 'Site23'})\n", 1)
    # Replace older warning text, now stale because excluded regions aren't offered.
    source = source.replace('Known data issues: LM8 incomplete; Site20 and Site23 reported misaligned. Downloading does not validate alignment. Actual raster data is needed for maps, horizons and new candidate measurements.',
                            'Three unreliable regions (LM8, Site20 and Site23) are excluded from the current release catalogue. Full-resolution NASA layers are required for new maps, measurements and horizons.')
    source = source.replace('Browse all 27 lunar regions offline.', 'Browse the 24 currently included lunar regions offline.')
    return source


def change_settings(source: str) -> str:
    if TAG in source:
        return source
    marker = "    style += f'''\\nQMainWindow,QWidget {{font-size:{s['font_size']}px;}}"
    if source.count(marker) != 1:
        raise ValueError('Unrecognized settings_store stylesheet; settings not changed')
    css = '''    # SELENEKTO_FINAL_CONSOLIDATION_V1: deep Obsidian palette, preserving accent colours and Graphite.\n    if s['theme'] == 'Obsidian':\n        style += """\n        QMainWindow, QWidget { background-color: #06070A; color: #F1F2F5; }\n        QFrame#sidebar, QGroupBox, QTableWidget, QListWidget, QTextEdit, QScrollArea {\n            background-color: #0D1016; border: 1px solid #252B35;\n        }\n        QPushButton { background-color: #161B24; color: #F1F2F5; border: 1px solid #343E4B; }\n        QPushButton:hover { background-color: #222A36; }\n        QComboBox, QLineEdit, QSpinBox, QDateEdit, QDateTimeEdit {\n            background-color: #0C1016; color: #F1F2F5; border: 1px solid #384251;\n        }\n        QComboBox QAbstractItemView { background-color: #10141D; color: #F1F2F5; }\n        QHeaderView::section { background-color: #151A23; color: #F1F2F5; }\n        QTableWidget { alternate-background-color: #121722; }\n        QListWidget::item:selected { background-color: #222B3A; color: white; }\n        """\n'''
    return source.replace(marker, css + marker, 1)


def change_builder(source: str) -> str:
    if TAG in source:
        return source
    anchor = "    print('Portable directory:',dest)"
    if source.count(anchor) != 1:
        raise ValueError('Cannot locate portable builder output; build script not changed')
    extra = """    # SELENEKTO_FINAL_CONSOLIDATION_V1 — omit excluded catalogues from PUBLIC distribution only.
    # This acts only on the fresh dist output; never on source NASA data or saved candidates.
    for region in ('LM8', 'Site20', 'Site23'):
        for subfolder in ('data/catalog/previews', 'data/catalog/region_profiles'):
            folder = dest/subfolder
            if folder.is_dir():
                for path in folder.glob(region + '_*'):
                    if path.is_file():
                        path.unlink()
    # Do not package obsolete pre-exclusion previews/profiles.
"""
    return source.replace(anchor, extra + anchor, 1)


def main():
    files = [
        (ROOT/'scripts/launch_selenekto_v2_controls.py', change_launcher),
        (ROOT/'src/selenekto_v2/library_view.py', change_library),
        (ROOT/'src/selenekto_v2/settings_store.py', change_settings),
        (ROOT/'scripts/build_windows_release.py', change_builder),
    ]
    updates=[]
    for path, transform in files:
        if not path.is_file():
            raise FileNotFoundError(f'Missing required file: {path}')
        before=path.read_text(encoding='utf-8')
        after=transform(before)
        ast.parse(after, filename=str(path))
        updates.append((path,before,after))
    stamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    for path,before,after in updates:
        if before==after:
            print(f'ALREADY PATCHED: {path.relative_to(ROOT)}')
            continue
        backup=path.with_name(f'{path.stem}_pre_final_{stamp}{path.suffix}.bak')
        backup.write_text(before,encoding='utf-8')
        path.write_text(after,encoding='utf-8')
        print(f'UPDATED: {path.relative_to(ROOT)} (backup {backup.name})')
    print('Excluded from released region views: LM8, Site20, Site23.')
    print('Obsidian is near-black again. No NASA data or candidates were deleted.')

if __name__=='__main__':
    try: main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr)
        sys.exit(1)
