"""Offline conversion of installed PGDA GeoTIFF regions to versioned JSON profiles.

Five original rasters remain authoritative. JSON is metadata, not a lossless copy
of 10+ million elevation samples per layer.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

LAYERS = {
    'elevation': ('surf', 'm'),
    'measurement_count': ('ldec', 'LOLA spots per pixel'),
    'elevation_uncertainty': ('toterr', 'RMS error (m)'),
    'slope': ('slp', 'degrees'),
    'slope_uncertainty': ('slperr', 'RMS error (degrees)'),
}


def raster_paths(raw_root: Path, region: str) -> dict[str, Path]:
    return {key: raw_root / region / f'{region}_final_adj_5mpp_{suffix}.tif'
            for key, (suffix, _) in LAYERS.items()}


def finite_statistics(dataset, *, block_pixels: int = 512, measurement_count: bool = False):
    """Exact min/max/mean/population standard deviation and valid-pixel count.

    Median and percentiles are overview-sampled, intentionally marked approximate.
    Never treats NaN, infinite or raster-masked cells as valid observations.
    """
    import numpy as np
    from rasterio.windows import Window
    from rasterio.enums import Resampling
    total = int(dataset.width * dataset.height)
    count = 0
    total_sum = 0.0
    total_squares = 0.0
    lo, hi = float('inf'), float('-inf')
    positive = 0
    counts = {}
    for row in range(0, dataset.height, block_pixels):
        h = min(block_pixels, dataset.height - row)
        for col in range(0, dataset.width, block_pixels):
            w = min(block_pixels, dataset.width - col)
            arr = dataset.read(1, window=Window(col, row, w, h), masked=True)
            data = np.asarray(arr.data)
            keep = (~np.ma.getmaskarray(arr)) & np.isfinite(data)
            vals = data[keep].astype(np.float64)
            if vals.size == 0:
                continue
            count += int(vals.size)
            total_sum += float(np.sum(vals))
            total_squares += float(np.dot(vals, vals))
            lo = min(lo, float(vals.min()))
            hi = max(hi, float(vals.max()))
            if measurement_count:
                positive += int(np.count_nonzero(vals > 0))
                unique, frequencies = np.unique(vals.astype(np.int64), return_counts=True)
                for k, v in zip(unique, frequencies):
                    counts[int(k)] = counts.get(int(k), 0) + int(v)
    result = {
        'total_pixels': total,
        'valid_pixels': count,
        'missing_or_masked_pixels': total - count,
        'valid_coverage_percent': 100.0 * count / total if total else 0.0,
    }
    if not count:
        result.update(minimum=None, maximum=None, mean=None, median=None,
                      standard_deviation_population=None, percentile_02=None,
                      percentile_98=None, statistic_status='no_valid_pixels')
        return result
    mean = total_sum / count
    result.update(minimum=lo, maximum=hi, mean=mean,
                  standard_deviation_population=float(max(0.0, total_squares / count - mean * mean) ** 0.5),
                  statistic_status='valid')
    # Deterministic spatial overview sample: fast and bounded memory, not exact quantiles.
    oh, ow = min(512, dataset.height), min(512, dataset.width)
    overview = dataset.read(1, out_shape=(oh, ow), masked=True, resampling=Resampling.nearest)
    sample = np.asarray(overview.data)[(~np.ma.getmaskarray(overview)) & np.isfinite(overview.data)]
    result['median'] = float(np.median(sample)) if sample.size else None
    result['percentile_02'] = float(np.percentile(sample, 2)) if sample.size else None
    result['percentile_98'] = float(np.percentile(sample, 98)) if sample.size else None
    result['quantile_method'] = 'approximate: 512x512 nearest-neighbour overview sample (not exact full-raster quantiles)'
    if counts:
        result['spot_count_distribution'] = [{'spots_per_pixel': k, 'pixel_count': v,
                                             'percentage_of_valid_pixels': 100 * v / count}
                                            for k, v in sorted(counts.items())]
        result['pixels_with_at_least_one_spot'] = positive
        result['pixels_with_at_least_one_spot_percent'] = 100 * positive / count
    return result


def inspect_region(raw_root: Path, region: str, name: str = '') -> dict:
    import rasterio
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    paths = raster_paths(raw_root, region)
    profile = {
        'schema_version': '1.1', 'report_type': 'selenekto_site_terrain_profile',
        'generated_utc': now, 'site_code': region, 'region_name': name or region,
        'source': 'NASA/GSFC PGDA, LOLA 5m/pixel south-polar terrain products',
        'grid': None, 'layers': {}, 'dataset_provenance': [],
        'availability': 'incomplete', 'errors': [],
        'scientific_interpretation_limits': [
            'JSON stores per-layer statistical summaries, not all pixel values.',
            'Full-resolution source GeoTIFF files remain authoritative.',
            'NoData is not zero, and LDEC zero is not necessarily missing elevation.',
            'This report does not establish landing safety, sunlight, or Earth visibility.',
            'Quantiles use a spatial overview sample; min/max/mean/std and valid counts are full-raster.',
        ],
    }
    ref = None
    for key, path in paths.items():
        unit = LAYERS[key][1]
        if not path.is_file():
            profile['errors'].append(f'{key}: missing file {path.name}')
            profile['layers'][key] = {'source_file': path.name, 'unit_from_product_documentation': unit,
                                      'status': 'missing_file', 'statistics': None}
            continue
        try:
            with rasterio.open(path) as ds:
                if ds.count != 1 or ds.crs is None or ds.width <= 0 or ds.height <= 0:
                    raise ValueError('expected a single-band raster with a CRS and valid dimensions')
                geom = (ds.width, ds.height, tuple(ds.transform), ds.crs.to_wkt())
                if ref is None:
                    ref = geom
                    profile['grid'] = {
                        'width': ds.width, 'height': ds.height, 'crs_wkt': ds.crs.to_wkt(),
                        'transform': list(ds.transform)[:6], 'bounds': list(ds.bounds),
                        'resolution_xy_m': [abs(ds.transform.a), abs(ds.transform.e)],
                        'pixel_count': ds.width * ds.height, 'all_five_layers_match': False,
                        'note': 'Projected lunar coordinates; verify geodetic conventions before solar or horizon geometry.',
                    }
                if geom != ref:
                    profile['errors'].append(f'{key}: grid mismatch')
                    profile['layers'][key] = {'source_file': path.name, 'unit_from_product_documentation': unit,
                                              'status': 'grid_mismatch', 'statistics': None}
                    continue
                # Special-case measurement count without modifying Rasterio dataset.
                stats = finite_statistics(ds, measurement_count=(key == "measurement_count"))
                profile['layers'][key] = {
                    'source_file': path.name, 'unit_from_product_documentation': unit,
                    'status': 'ready' if stats['valid_pixels'] else 'all_nodata', 'statistics': stats,
                }
                if stats['valid_pixels'] == 0:
                    profile['errors'].append(f'{key}: all pixels are NoData')
                profile['dataset_provenance'].append({
                    'path': str(path.relative_to(raw_root.parent.parent)),
                    'file_size_bytes': path.stat().st_size,
                    'hash_status': 'not_checked (file CRC/SHA256 requires separate manifest)',
                })
        except Exception as exc:
            profile['errors'].append(f'{key}: {type(exc).__name__}: {str(exc)[:240]}')
            profile['layers'][key] = {'source_file': path.name, 'unit_from_product_documentation': unit,
                                      'status': 'invalid_file', 'statistics': None}
    statuses = [v['status'] for v in profile['layers'].values()]
    if all(v == 'ready' for v in statuses) and len(statuses) == 5:
        profile['availability'] = 'ready'
        profile['grid']['all_five_layers_match'] = True
    elif any(v in ('invalid_file', 'grid_mismatch') for v in statuses):
        profile['availability'] = 'invalid_or_misaligned'
    elif any(v == 'all_nodata' for v in statuses):
        profile['availability'] = 'contains_all_nodata_layer'
    else:
        profile['availability'] = 'incomplete'
    return profile


def generate_catalogue(raw_root: Path, output_root: Path, regions: Mapping[str, str]):
    """Always emits one JSON for each requested region, including incomplete ones."""
    output_root.mkdir(parents=True, exist_ok=True)
    listing = []
    for reg, name in regions.items():
        report = inspect_region(raw_root, reg, name)
        file = output_root / f'{reg}_terrain_profile.json'
        file.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        listing.append({'site_code': reg, 'region_name': name, 'status': report['availability'],
                        'file': file.name, 'errors': report['errors'],
                        'valid_layers': sum(v['status'] == 'ready' for v in report['layers'].values())})
        yield listing[-1]
    (output_root / 'regions_index.json').write_text(json.dumps({
        'schema_version': '1.1', 'regions': listing,
        'total_regions': len(listing), 'ready_regions': sum(r['status'] == 'ready' for r in listing),
        'note': 'Incomplete or invalid entries are not usable for analysis. Refer to per-region report.'
    }, indent=2, ensure_ascii=False), encoding='utf-8')
