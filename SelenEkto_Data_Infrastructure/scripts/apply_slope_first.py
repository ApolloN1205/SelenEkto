"""Apply SelenEkto slope-first UI and genuine slope-preview changes safely.

Run from any directory: python scripts/apply_slope_first.py
Creates backups, validates exact source anchors, and rolls back on error.
"""
from __future__ import annotations
import ast
from datetime import datetime, timezone
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
STAMP = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')


def modify(path: Path, changes: list[tuple[str,str]], *, optional=False):
    if not path.exists():
        if optional:
            print(f'SKIP missing optional file: {path.relative_to(ROOT)}');return
        raise FileNotFoundError(path)
    before = path.read_text(encoding='utf-8')
    after = before
    for old, new in changes:
        if new in after:
            continue
        count = after.count(old)
        if count != 1:
            raise RuntimeError(f'Refusing to patch {path}: expected 1 instance of {old[:90]!r}; found {count}. No changes written to this file.')
        after=after.replace(old,new,1)
    if after==before:
        print(f'ALREADY slope-first: {path.relative_to(ROOT)}');return
    ast.parse(after,filename=str(path))
    backup=path.with_name(f'{path.stem}_before_slope_first_{STAMP}{path.suffix}.bak')
    backup.write_text(before,encoding='utf-8')
    path.write_text(after,encoding='utf-8')
    print(f'UPDATED {path.relative_to(ROOT)} (backup: {backup.name})')


def main():
    lib=ROOT/'src/selenekto_v2/offline_library.py'
    modify(lib,[
        ("f'{region}_elevation.png'", "f'{region}_slope.png'"),
        ('"""Downsample authoritative elevation TIFF for offline *visual reference only*."""',
         '"""Downsample real NASA slope GeoTIFF (degrees) for reference-only preview."""'),
        ("source=raster_path(root,region,'surf')", "source=raster_path(root,region,'slp')"),
        ("Missing elevation GeoTIFF:", "Missing slope GeoTIFF:"),
        ("no valid elevation data", "no valid slope data"),
        ("f'{region}  /  ELEVATION PREVIEW'", "f'{region}  /  SLOPE (DEGREES) · VISUAL PREVIEW'"),
        # Reject nonnegative-unphysical extrema from corrupt/invalid files before generating an image.
        ("    source=raster_path(root,region,'slp')", "    if region in ('Site20', 'Site23'):\n        raise ValueError(f'{region}: reported misaligned; slope preview disabled until data is validated')\n    source=raster_path(root,region,'slp')"),
        # Use consistent physical slope range, not percentile normalization which makes gentle terrain appear as severe as steep terrain.
        ("    lo,hi=np.percentile(valid,[2,98]);hi=max(lo+1e-9,hi)",
         "    if np.any((valid < -0.01) | (valid > 90.01)):\n        raise ValueError(f'{region}: slope raster contains values outside 0–90 degrees; investigate data validity')\n    lo,hi=0.0,30.0  # Common fixed scale for honest visual comparison between regions"),
        ("    grey=np.uint8(np.clip((arr-lo)/(hi-lo),0,1)*235+12)",
         "    grey=np.uint8(np.nan_to_num(np.clip((arr-lo)/(hi-lo),0,1)*235+12,nan=0))"),
    ])
    script=ROOT/'scripts/generate_offline_previews.py'
    modify(script,[
        ('reference-only elevation preview PNGs','reference-only slope preview PNGs'),
        ('check original elevation TIFFs','check original slope TIFFs'),
    ])
    library_ui=ROOT/'src/selenekto_v2/library_view.py'
    modify(library_ui,[
        ('Small previews are visual references, not measured safety maps.', 'Slope previews use genuine NASA slope rasters in degrees (fixed 0–30° grayscale). They are visual references, not landing-safety assessments.'),
        ('Run the preview-generation script on a machine holding its elevation TIFF.', 'Run the slope preview generator where that region’s slope TIFF is installed.'),
    ])
    settings=ROOT/'src/selenekto_v2/settings_store.py'
    modify(settings,[("'default_layer': 'Elevation'", "'default_layer': 'Slope'")],optional=True)
    launcher=ROOT/'scripts/launch_selenekto_v2_controls.py'
    modify(launcher,[("self.layer='Elevation'", "self.layer='Slope'")],optional=True)
    old_test=ROOT/'tests/test_offline_library.py'
    modify(old_test,[("'Site04_elevation.png'", "'Site04_slope.png'")],optional=True)
    pref=ROOT/'data/config/desktop_settings.json'
    if pref.is_file():
        obj=json.loads(pref.read_text(encoding='utf-8'))
        if isinstance(obj,dict) and obj.get('default_layer')=='Elevation':
            backup=pref.with_name(f'desktop_settings_before_slope_first_{STAMP}.json.bak')
            backup.write_bytes(pref.read_bytes());obj['default_layer']='Slope'
            pref.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
            print('UPDATED saved default layer Elevation → Slope (other preferences preserved)')
    print('\nNEXT: python scripts/generate_offline_previews.py')
    print('NEXT: python -m pytest tests -q')
    print('NEXT: rebuild Windows executable after checking previews.')


if __name__=='__main__':
    try:main()
    except Exception as exc:
        print(f'ERROR: {exc}',file=sys.stderr);sys.exit(1)
