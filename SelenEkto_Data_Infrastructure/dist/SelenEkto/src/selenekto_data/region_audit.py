"""Read-only health checks for downloaded NASA PGDA region GeoTIFFs.

A missing layer, an unreadable/misaligned layer, and a NoData pixel
are different conditions and must not be conflated.
"""
from __future__ import annotations
from pathlib import Path
import math


def classify_region(root, region, expected_layers):
    """Return a JSON-serialisable region audit. Never modify any files."""
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    statuses = {}
    geometry = None
    sampled_data = {}
    for layer, path in expected_layers.items():
        path = Path(path)
        if not path.exists():
            statuses[layer] = {'status': 'missing_file', 'path': str(path)}
            continue
        if not path.is_file() or path.stat().st_size == 0:
            statuses[layer] = {'status': 'invalid_file', 'path': str(path), 'reason': 'not a nonempty file'}
            continue
        try:
            with rasterio.open(path) as ds:
                if ds.count != 1 or ds.crs is None or ds.width <= 0 or ds.height <= 0:
                    raise ValueError('expected one band, valid dimensions and CRS')
                geom = (ds.width, ds.height, tuple(ds.transform), str(ds.crs))
                if geometry is None:
                    geometry = geom
                if geometry != geom:
                    statuses[layer] = {'status': 'grid_mismatch', 'path': str(path)}
                    continue
                data = ds.read(1, out_shape=(min(ds.height, 128), min(ds.width, 128)),
                               resampling=Resampling.nearest, masked=True)
                mask = np.ma.getmaskarray(data) | ~np.isfinite(np.ma.getdata(data))
                valid = int((~mask).sum())
                total = int(mask.size)
                sampled_data[layer] = {'sampled_valid_pixels': valid, 'sampled_total_pixels': total,
                                       'sampled_missing_percent': round(100 * (total-valid)/total, 2)}
                statuses[layer] = {'status': 'ready' if valid else 'sample_only_nodata',
                                   'path': str(path), **sampled_data[layer]}
        except Exception as exc:
            statuses[layer] = {'status': 'invalid_file', 'path': str(path), 'reason': str(exc)[:500]}
    flags = [item['status'] for item in statuses.values()]
    if 'missing_file' in flags:
        status = 'incomplete'
    elif any(v in flags for v in ('invalid_file', 'grid_mismatch')):
        status = 'invalid_or_misaligned'
    elif 'sample_only_nodata' in flags:
        status = 'sample_has_no_data'
    elif len(statuses) == len(expected_layers):
        status = 'ready'
    else:
        status = 'incomplete'
    return {'region': region, 'status': status, 'layers': statuses,
            'note': 'NoData percentages are from a sparse 128x128 overview sample, NOT an exact full-raster census.'}


def describe_pixel(metrics):
    """Human-readable explanation for missing candidate metrics."""
    missing = [key for key, value in metrics.items() if value is None]
    if not missing:
        return 'All five terrain values available at this pixel.'
    return 'NoData or unavailable layer at selected pixel: ' + ', '.join(missing) + '. This is not a zero value.'
