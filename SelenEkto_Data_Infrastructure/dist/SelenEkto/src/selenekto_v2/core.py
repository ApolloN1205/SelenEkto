"""SelenEkto 2.0 storage and region data checks. No GUI dependency.

Uses existing 5m PGDA TIFFs; region profiles describe metadata only.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import tempfile

SUFFIXES = {"Elevation": "surf", "Slope": "slp", "Elevation uncertainty": "toterr", "Slope uncertainty": "slperr", "LOLA observations": "ldec"}
METRICS = {"Elevation": "elevation_m", "Slope": "slope_deg", "Elevation uncertainty": "elevation_rms_m", "Slope uncertainty": "slope_rms_deg", "LOLA observations": "lola_spot_count"}


def region_names(root: Path):
    """Discover from generated profiles AND from genuine local region folders."""
    raw = root / 'data/raw/lola'
    profiles = root / 'data/catalog/region_profiles'
    names = {p.name.removesuffix('_terrain_profile.json') for p in profiles.glob('*_terrain_profile.json')} if profiles.exists() else set()
    if raw.exists():
        names.update(p.name for p in raw.iterdir() if p.is_dir())
    return sorted(names)


def region_files(root: Path, region: str):
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


def region_health(root: Path, region: str):
    paths = region_files(root, region)
    missing = [label for label, path in paths.items() if path is None or not path.exists()]
    if missing:
        return {'region': region, 'status':'incomplete', 'details': 'Missing: ' + ', '.join(missing), 'missing': missing}
    try:
        import rasterio
        ref = None
        for label, path in paths.items():
            with rasterio.open(path) as ds:
                if ds.count != 1 or ds.crs is None:
                    return {'region': region,'status':'invalid', 'details':f'{label}: missing CRS / bad bands','missing': []}
                geom = (ds.width, ds.height, tuple(ds.transform), ds.crs.to_wkt())
                if ref is not None and geom != ref:
                    return {'region':region, 'status':'misaligned', 'details':f'{label}: grid mismatch','missing': []}
                ref = geom
    except Exception as e:
        return {'region': region, 'status':'invalid', 'details':str(e)[:160], 'missing': []}
    return {'region':region,'status':'ready','details':'Five readable, aligned rasters (pixel NoData still possible)','missing': []}


def raster_overview(root: Path, region: str, layer: str, max_size=850):
    """Masked overview only; avoid reading huge arrays into the interface."""
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    path = region_files(root, region)[layer]
    with rasterio.open(path) as ds:
        scale = min(1.0, max_size/max(ds.width, ds.height))
        h, w = max(1,int(ds.height*scale)), max(1,int(ds.width*scale))
        arr = ds.read(1, out_shape=(h,w), masked=True, resampling=Resampling.nearest)
        data = np.asarray(arr.data, dtype=float)
        data[np.ma.getmaskarray(arr) | ~np.isfinite(data)] = np.nan
        return data, (ds.height, ds.width)


def read_cell(root: Path, region: str, row: int, col: int):
    import rasterio
    import numpy as np
    paths = region_files(root, region)
    result = {'region':region,'row':int(row),'col':int(col)}
    for layer, path in paths.items():
        with rasterio.open(path) as ds:
            if not (0 <= row < ds.height and 0 <= col < ds.width):
                raise ValueError('Pixel outside raster')
            masked = ds.read(1, window=((row,row+1),(col,col+1)),masked=True)
            z = masked[0,0]
            value = float(z) if not np.ma.is_masked(z) and np.isfinite(z) else None
            result[METRICS[layer]] = value
            if layer == 'Elevation':
                x,y = ds.transform * (col+.5,row+.5)
                result['x_projected_m']=float(x);result['y_projected_m']=float(y)
    return result


def validate_name(name):
    if not isinstance(name,str): raise ValueError('Name must be text')
    name = ' '.join(name.strip().split())
    if not (1 <= len(name) <= 64) or name[0] in '=+-@':
        raise ValueError('Use a name of 1–64 characters without a spreadsheet formula prefix')
    return name


def normalize_record(record):
    required=('name','region','row','col')
    if any(k not in record for k in required): raise ValueError('Candidate record missing required field')
    out = dict(record)
    out['name'] = validate_name(out['name'])
    out['region'] = str(out['region'])
    if not out['region'].isalnum(): raise ValueError('Invalid region ID')
    out['row'],out['col']=int(out['row']),int(out['col'])
    if out['row'] < 0 or out['col'] < 0: raise ValueError('Invalid pixel position')
    for k in METRICS.values():
        z=out.get(k)
        out[k]=float(z) if z is not None and z != '' and math.isfinite(float(z)) else None
    return out


def candidates_path(root: Path):
    return root/'data/catalog/named_candidates.json'


def load_candidates(root: Path):
    path=candidates_path(root)
    if path is None or not path.exists(): return []
    parsed=json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(parsed,dict) or not isinstance(parsed.get('candidates'),list): raise ValueError('Invalid candidate store')
    return [normalize_record(x) for x in parsed['candidates']]


def save_candidates(root: Path, candidates):
    path=candidates_path(root); path.parent.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':1, 'purpose':'named candidate coordinates and pixel metrics; not landing safety',
             'candidates':[normalize_record(x) for x in candidates]}
    # atomic replacement: previous file not lost if write fails
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as f:
        tmp=Path(f.name)
        json.dump(payload,f,indent=2,ensure_ascii=False,allow_nan=False)
    try: os.replace(tmp,path)
    finally: tmp.unlink(missing_ok=True)
    return path


def comparable(records, indices):
    if len(indices)<2 or len(set(indices))!=len(indices): raise ValueError('Select two or more different candidates')
    if any(i<0 or i>=len(records) for i in indices):raise ValueError('Candidate index out of range')
    return [records[i] for i in indices]
