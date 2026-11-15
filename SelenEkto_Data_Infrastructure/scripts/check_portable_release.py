"""Inspect SelenEkto portable directory without Python dependencies or NASA data."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path


def inspect_release(root: Path) -> dict:
    root = Path(root)
    required = ('SelenEkto.exe', 'scripts/launch_selenekto_v2_controls.py',
                'src/selenekto_v2/library_view.py', 'src/selenekto_v2/offline_library.py')
    missing = [name for name in required if not (root / name).is_file()]
    preview_dir = root / 'data' / 'catalog' / 'previews'
    previews = list(preview_dir.glob('*_slope.png')) if preview_dir.is_dir() else []
    raw = root / 'data' / 'raw' / 'lola'
    linked = bool(raw.is_symlink() or (os.name == 'nt' and raw.exists() and os.path.isjunction(raw)))
    tiffs = list(raw.rglob('*.tif')) if raw.is_dir() and not linked else []
    total = sum(p.stat().st_size for p in root.rglob('*') if p.is_file() and not p.is_symlink() and not linked_external(p, raw, linked))
    return {'root': str(root), 'missing_required': missing, 'slope_previews': len(previews),
            'raw_data_junction': linked, 'embedded_tiff_count': len(tiffs),
            'approx_mb_excluding_linked_raw': round(total / 1048576, 1),
            'portable_ready_for_smoke_test': not missing and bool(previews) and not linked and not tiffs}


def linked_external(path: Path, raw: Path, linked: bool) -> bool:
    if not linked:
        return False
    try:
        path.relative_to(raw)
        return True
    except ValueError:
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,default=Path(__file__).resolve().parents[1]/'dist'/'SelenEkto')
    args=parser.parse_args()
    result=inspect_release(args.folder)
    print(json.dumps(result,indent=2))
    if result['raw_data_junction']:
        print('WARNING: This is a local development build with an external NASA data link. Do not distribute.')
    if not result['slope_previews']:
        print('WARNING: No slope previews packaged; the clean app will show only a catalogue and missing-data notices.')
    return 0 if result['portable_ready_for_smoke_test'] else 2

if __name__=='__main__':
    raise SystemExit(main())
