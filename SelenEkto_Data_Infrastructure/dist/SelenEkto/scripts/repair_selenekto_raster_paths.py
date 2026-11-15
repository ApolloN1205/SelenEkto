"""Targeted SelenEkto compatibility repair for two path-resolution regressions.

Run from SelenEkto_Data_Infrastructure with its .venv. Does not touch any NASA data.
Replaces only the functions `find_rasters` and `region_files`; backs up source files.
"""
from __future__ import annotations
import ast
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1] if Path(__file__).resolve().parent.name == 'scripts' else Path.cwd()

FIND_RASTERS = '''def find_rasters(raw: Path, region: str) -> dict:
    """Find a region's own TIFFs, including nested downloads; never cross regions."""
    if not region or not region.isalnum():
        raise ValueError('Invalid region code')
    from pathlib import Path
    raw = Path(raw)
    result = {}
    for layer, suffix in SUFFIX.items():
        filename = f'{region}_final_adj_5mpp_{suffix}.tif'
        canonical = raw / region / filename
        if canonical.is_file():
            result[layer] = canonical
            continue
        # Include recognised nested layouts such as raw/downloads/Site04/...
        matches = sorted(p for p in raw.rglob(filename) if p.is_file()) if raw.is_dir() else []
        matches = [p for p in matches if region in p.relative_to(raw).parts[:-1]]
        result[layer] = matches[0] if len(matches) == 1 else None
    return result
'''

REGION_FILES = '''def region_files(root: Path, region: str):
    """Return discovered TIFFs or canonical expected paths for missing layers."""
    if not region or not region.isalnum():
        raise ValueError('Invalid region ID')
    from selenekto_v2.actual_regions import find_rasters
    raw = Path(root) / 'data/raw/lola'
    found = find_rasters(raw, region)
    mapping = {'Elevation': 'elevation', 'Slope': 'slope',
               'Elevation uncertainty': 'elevation_uncertainty',
               'Slope uncertainty': 'slope_uncertainty',
               'LOLA observations': 'measurement_count'}
    return {label: found.get(layer) or raw / region / f'{region}_final_adj_5mpp_{SUFFIXES[label]}.tif'
            for label, layer in mapping.items()}
'''

def replace_function(path: Path, name: str, replacement: str):
    if not path.is_file():
        raise FileNotFoundError(f'Missing source file: {path}')
    text = path.read_text(encoding='utf-8')
    tree = ast.parse(text, filename=str(path))
    functions = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name]
    if len(functions) != 1:
        raise ValueError(f'Expected exactly one {name} function in {path}; found {len(functions)}; no changes made')
    node = functions[0]
    lines = text.splitlines(keepends=True)
    newline = '\r\n' if '\r\n' in text else '\n'
    updated = ''.join(lines[:node.lineno-1]) + replacement.replace('\n', newline) + ''.join(lines[node.end_lineno:])
    compile(updated, str(path), 'exec')
    if updated == text:
        print(f'Already patched: {path.name}::{name}')
        return
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup = path.with_name(f'{path.stem}.before_raster_fix_{stamp}{path.suffix}')
    shutil.copy2(path, backup)
    path.write_text(updated, encoding='utf-8', newline='')
    print(f'Patched {path.relative_to(ROOT)} (backup: {backup.name})')

def main():
    pkg = ROOT / 'src' / 'selenekto_v2'
    paths = [(pkg/'actual_regions.py','find_rasters',FIND_RASTERS),
             (pkg/'core.py','region_files',REGION_FILES)]
    if any(not p.is_file() for p,_,_ in paths):
        for p,_,_ in paths:
            if not p.is_file(): print('MISSING:',p)
        return 1
    for path,name,replacement in paths:
        replace_function(path,name,replacement)
    print('Done. No GeoTIFFs, JSON profiles, or candidates were modified.')
    return 0

if __name__ == '__main__':
    sys.exit(main())
