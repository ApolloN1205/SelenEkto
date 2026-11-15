"""Locate genuine local PGDA terrain rasters within one region directory.

Does not mix regions, download, rename, or synthesize raster data.
"""
from pathlib import Path

SUFFIX = {
    'elevation': 'surf', 'slope': 'slp',
    'elevation_uncertainty': 'toterr', 'slope_uncertainty': 'slperr',
    'measurement_count': 'ldec'
}
ALIASES = {
    'surf': ('surf', 'elevation', 'ldem'),
    'slp': ('slp', 'slope'),
    'toterr': ('toterr', 'elevation_uncertainty', 'zerr'),
    'slperr': ('slperr', 'slope_uncertainty'),
    'ldec': ('ldec', 'measurement_count', 'lola_count'),
}


def resolve_region(raw_root: Path, region: str):
    """Return {layer:path|None}, errors; report ambiguity instead of guessing."""
    if not region.isalnum():
        raise ValueError('Invalid region code')
    folder = Path(raw_root) / region
    paths = {}
    issues = []
    if not folder.is_dir():
        return {k: None for k in SUFFIX}, [f'Not a directory: {folder}']
    rasters = sorted((p for p in folder.rglob('*')
                      if p.is_file() and p.suffix.lower() in {'.tif', '.tiff'}),
                     key=lambda p: str(p).lower())
    for layer, suffix in SUFFIX.items():
        canonical = folder / f'{region}_final_adj_5mpp_{suffix}.tif'
        if canonical.is_file():
            paths[layer] = canonical
            continue
        valid_names = {f'{region.lower()}_final_adj_5mpp_{suffix}.tif',
                       f'{region.lower()}_final_adj_5mpp_{suffix}.tiff'}
        exact = [p for p in rasters if p.name.lower() in valid_names]
        if len(exact) == 1:
            paths[layer] = exact[0]
            continue
        # Fallback must have explicit, unambiguous terminal product token.
        aliases = ALIASES[suffix]
        matches = [p for p in rasters if any(
            p.stem.lower() == word or p.stem.lower().endswith('_' + word)
            for word in aliases)]
        if len(matches) == 1:
            paths[layer] = matches[0]
        else:
            paths[layer] = None
            issues.append(f'{layer}: ' + ('no recognised TIFF found' if not matches
                          else f'ambiguous TIFFs: {", ".join(p.name for p in matches)}'))
    return paths, issues


def inventory(raw_root: Path, region: str):
    directory = Path(raw_root) / region
    files = sorted((p for p in directory.rglob('*') if p.is_file()), key=lambda p:str(p)) if directory.is_dir() else []
    located, issues = resolve_region(raw_root,region)
    return {'region':region, 'folder_exists':directory.is_dir(),
            'files_on_disk':len(files),
            'tiff_count':sum(p.suffix.lower() in ('.tif','.tiff') for p in files),
            'example_files':[str(p.relative_to(directory)) for p in files[:12]],
            'found_layers':sum(p is not None for p in located.values()),
            'resolved_files':{key:(str(path) if path else None) for key,path in located.items()},
            'issues':issues}
