"""Read and enrich real SelenEkto region terrain-profile JSON files.

No synthetic region metrics: missing values remain null. Existing raster-derived
statistics are retained unchanged, with a human-readable machine-queryable summary.
"""
from __future__ import annotations
import json
import math
import os
import tempfile
from pathlib import Path

LAYER_METRICS = {
    'elevation': ('elevation', 'metres'),
    'slope': ('slope', 'degrees'),
    'elevation_uncertainty': ('elevation_uncertainty', 'RMS metres'),
    'slope_uncertainty': ('slope_uncertainty', 'RMS degrees'),
    'measurement_count': ('lola_observations', 'spots per pixel'),
}
METRIC_COLUMNS = {
    'Mean slope (°)': ('slope', 'mean'),
    'Median slope (°)': ('slope', 'median'),
    'Maximum slope (°)': ('slope', 'maximum'),
    'Mean elevation (m)': ('elevation', 'mean'),
    'Minimum elevation (m)': ('elevation', 'minimum'),
    'Maximum elevation (m)': ('elevation', 'maximum'),
    'Mean elevation uncertainty (m RMS)': ('elevation_uncertainty', 'mean'),
    'Mean slope uncertainty (° RMS)': ('slope_uncertainty', 'mean'),
    'Direct LOLA coverage (%)': ('lola_observations', 'pixels_with_at_least_one_spot_percent'),
}


def finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def readable_metrics(profile):
    """Assemble consistently shaped summaries from a profile's original layers."""
    result = {}
    layers = profile.get('layers') or {}
    for key, (display_key, unit) in LAYER_METRICS.items():
        entry = layers.get(key) or {}
        stats = entry.get('statistics') or {}
        status = entry.get('status') or 'missing_file'
        result[display_key] = {
            'status': status, 'units': unit,
            'minimum': finite_number(stats.get('minimum')),
            'maximum': finite_number(stats.get('maximum')),
            'mean': finite_number(stats.get('mean')),
            'median': finite_number(stats.get('median')),
            'standard_deviation': finite_number(stats.get('standard_deviation_population')),
            'valid_pixels': stats.get('valid_pixels'),
            'valid_coverage_percent': finite_number(stats.get('valid_coverage_percent')),
        }
        if key == 'measurement_count':
            result[display_key]['pixels_with_at_least_one_spot_percent'] = finite_number(
                stats.get('pixels_with_at_least_one_spot_percent'))
            result[display_key]['pixels_with_at_least_one_spot'] = stats.get('pixels_with_at_least_one_spot')
        result[display_key]['median_method'] = stats.get('quantile_method', 'unknown')
    return result


def enrich_profile(profile):
    if not isinstance(profile, dict) or not isinstance(profile.get('layers'), dict):
        raise ValueError('Expected an existing NASA raster-derived terrain profile with layers')
    enriched = dict(profile)
    enriched['readable_metrics'] = readable_metrics(profile)
    enriched['readable_metrics_note'] = (
        'Region-wide raster statistics; NOT measurements at an individual candidate. '
        'Median is approximate; NoData is excluded; missing rasters have null metrics. '
        'The original GeoTIFFs remain required for per-pixel and horizon analysis.'
    )
    return enriched


def load_profiles(folder: Path):
    profiles = []
    for path in sorted(Path(folder).glob('*_terrain_profile.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            profiles.append(enrich_profile(data))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            profiles.append({'site_code': path.name.replace('_terrain_profile.json',''),
                             'region_name': path.stem, 'availability':'invalid_profile',
                             'errors': [str(exc)], 'layers': {},
                             'readable_metrics': readable_metrics({})})
    return profiles


def metric_value(profile, label):
    layer, field = METRIC_COLUMNS[label]
    return finite_number((profile.get('readable_metrics') or {}).get(layer, {}).get(field))


def atomic_write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                     prefix='.selenekto-', suffix='.tmp', delete=False) as handle:
        temp = Path(handle.name)
        json.dump(data, handle, indent=2, ensure_ascii=False, allow_nan=False)
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def prepare_profiles(folder: Path):
    """Add readable_metrics to existing on-disk profiles. No changes to source statistics."""
    folder = Path(folder)
    if not folder.is_dir():
        raise FileNotFoundError(f'Profile directory does not exist: {folder}')
    results = []
    for path in sorted(folder.glob('*_terrain_profile.json')):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            output = enrich_profile(data)
            atomic_write_json(path, output)
            results.append({'region': output.get('site_code', path.stem),
                            'status': output.get('availability', 'unknown'),
                            'ready_layers': sum(x['status'] == 'ready' for x in output['readable_metrics'].values()),
                            'errors': output.get('errors', [])})
        except (OSError, ValueError, TypeError) as exc:
            results.append({'region': path.stem, 'status': 'profile_error',
                            'ready_layers': 0, 'errors': [str(exc)]})
    return results
