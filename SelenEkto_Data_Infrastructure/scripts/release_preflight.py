"""Read-only SelenEkto release preflight. Never downloads, deletes or rewrites datasets."""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REGION_CODES = ('DM1','DM2','Haworth','LM1','LM2','LM3','LM4','LM5','LM6','LM7','LM8',
                'NPA','NPB','NPC','NPD','Shoemaker','Site01','Site04','Site06',
                'Site07','Site11','Site20','Site20v2','Site23','Site42','SL2','SL3')
LAYER_SUFFIXES = ('surf', 'slp', 'ldec', 'toterr', 'slperr')
REQUIRED = ('PySide6','numpy','matplotlib','rasterio','pyproj')


def inspect_region(root: Path, code: str) -> dict:
    region = root / 'data' / 'raw' / 'lola' / code
    names = {p.name.casefold(): p for p in region.rglob('*') if p.is_file()} if region.is_dir() else {}
    files = {}
    for suffix in LAYER_SUFFIXES:
        matches = [p for p in names.values() if p.suffix.lower() in ('.tif','.tiff')
                   and p.stem.lower().endswith('_5mpp_' + suffix)]
        files[suffix] = {'present': bool(matches), 'name': matches[0].name if matches else None,
                         'bytes': matches[0].stat().st_size if matches else 0}
    have = sum(x['present'] for x in files.values())
    return {'code': code, 'files_found': have, 'file_presence': files,
            'presence_status': 'five_present' if have == 5 else 'incomplete',
            'note': 'Presence alone does not validate raster alignment or NoData coverage.'}


def audit(root: Path) -> dict:
    launcher = root / 'scripts' / 'launch_selenekto_v2_controls.py'
    logo = root / 'assets' / 'branding' / 'logo.png'
    profiles = root / 'data' / 'catalog' / 'region_profiles'
    report = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'project_root': str(root),
        'launcher': {'exists': launcher.is_file(), 'path': str(launcher)},
        'logo': {'exists': logo.is_file(), 'path': str(logo)},
        'dependencies': {name: importlib.util.find_spec(name) is not None for name in REQUIRED},
        'regions': [inspect_region(root, code) for code in REGION_CODES],
        'region_profiles_found': sum((profiles / (code+'_terrain_profile.json')).is_file() for code in REGION_CODES),
        'gitignore_raw_rasters': (root / '.gitignore').exists() or (root.parent / '.gitignore').exists(),
    }
    report['summary'] = {
        'regions_with_five_files': sum(r['files_found'] == 5 for r in report['regions']),
        'regions_incomplete': sum(r['files_found'] != 5 for r in report['regions']),
        'dependencies_present': sum(report['dependencies'].values()),
        'dependencies_expected': len(REQUIRED),
        'release_entry_ready': launcher.is_file() and all(report['dependencies'].values()),
    }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--save', action='store_true', help='Save compact JSON report')
    args = parser.parse_args()
    root = args.root.resolve()
    result = audit(root)
    print('SelenEkto release preflight')
    print('Launcher:', 'OK' if result['launcher']['exists'] else 'MISSING')
    print('Branding PNG:', 'OK' if result['logo']['exists'] else 'optional / missing')
    print('Dependencies:', ', '.join(f"{k}={'OK' if v else 'MISSING'}" for k,v in result['dependencies'].items()))
    print('Region profiles:', result['region_profiles_found'], '/ 27')
    print('Regions with 5 TIFF files:', result['summary']['regions_with_five_files'], '/ 27')
    print('IMPORTANT: This checks file presence only, not raster integrity or scientific validity.')
    for r in result['regions']:
        if r['files_found'] != 5:
            missing = ','.join(k for k,v in r['file_presence'].items() if not v['present'])
            print(f"  {r['code']}: {r['files_found']}/5 files; missing: {missing}")
    print('Known concerns to validate independently: LM8 (incomplete), Site20 and Site23 (reported misaligned).')
    if args.save:
        path = root / 'data' / 'processed' / 'release' / 'preflight.json'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result,indent=2),encoding='utf-8')
        print('Report:',path)
    return 0 if result['summary']['release_entry_ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
