"""Rebuild real terrain statistics for all PGDA regions from their five local GeoTIFFs.

Run inside SelenEkto_Data_Infrastructure with its active Python environment.
Does not download data or synthesize unknown measurements.
"""
from __future__ import annotations
import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from selenekto_data.region_profiles import inspect_region
from selenekto_data.unified_regions import REGIONS
from selenekto_v2.region_data import enrich_profile, METRIC_COLUMNS, metric_value, atomic_write_json


def rebuild(raw_root: Path, output_root: Path, regions: dict[str,str]):
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for idx, (code, name) in enumerate(regions.items(), 1):
        print(f'[{idx}/{len(regions)}] Reading actual NASA rasters: {code} / {name}', flush=True)
        try:
            source = inspect_region(raw_root, code, name)
            report = enrich_profile(source)
            report['analysis_origin'] = 'Recomputed from original installed NASA GeoTIFF raster values'
            report['generated_for'] = 'SELENEKTO real multi-region scientific comparison'
            report['site01_compatible_fields'] = ['site_code', 'region_name', 'grid', 'layers', 'dataset_provenance']
            report['derived_statistics_note'] = ('Min, max, mean, population std and pixel coverage are computed from all valid pixels. '
                'Median and 2nd/98th percentiles are approximate overview samples. '
                'Missing layers remain null; zero LOLA spot count is valid and not NoData.')
            report['generated_utc'] = datetime.now(timezone.utc).isoformat(timespec='seconds')
        except Exception as exc:
            report = {'site_code': code, 'region_name': name, 'availability':'analysis_failed',
                      'errors':[f'{type(exc).__name__}: {exc}'], 'layers': {}, 'grid':None,
                      'analysis_origin':'Attempted full NASA raster analysis; unable to produce verified statistics'}
        path = output_root / f'{code}_terrain_profile.json'
        atomic_write_json(path, report)
        row = {'region': code, 'name': name, 'status': report['availability'],
               'ready_layers': sum(v.get('status')=='ready' for v in report.get('layers',{}).values()),
               'errors': ' | '.join(report.get('errors',[]))}
        for label in METRIC_COLUMNS:
            row[label] = metric_value(report, label)
        rows.append(row)
        print(f"    {row['status']} / {row['ready_layers']}/5 valid layers", flush=True)
        if row['errors']: print('    '+row['errors'][:350],flush=True)
    with (output_root/'regions_comparable.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ['region','name','status'])
        writer.writeheader();writer.writerows(rows)
    atomic_write_json(output_root/'regions_index.json', {
        'schema_version':'2.0-real-raster-regions', 'total_regions':len(rows),
        'ready_regions':sum(r['status']=='ready' for r in rows),
        'incomplete_regions': [r['region'] for r in rows if r['status']!='ready'],
        'regions': [{'site_code':r['region'],'region_name':r['name'], 'status':r['status'],
                     'ready_layers':r['ready_layers'],'file':r['region']+'_terrain_profile.json',
                     'errors':r['errors']} for r in rows]})
    return rows


def main():
    parser=argparse.ArgumentParser(description='Analyze ALL actual installed NASA PGDA regions to Site01-format JSON')
    parser.add_argument('--regions',nargs='*', choices=list(REGIONS), help='Optional regions (default all)')
    args=parser.parse_args()
    selected={key:REGIONS[key] for key in (args.regions or list(REGIONS))}
    print('SELENEKTO | NASA RASTER -> REAL JSON / NO FABRICATED DATA',flush=True)
    rows=rebuild(ROOT/'data/raw/lola', ROOT/'data/catalog/region_profiles', selected)
    print(f"DONE: {len(rows)} profiles, {sum(x['status']=='ready' for x in rows)} fully usable",flush=True)
    print('CSV: data/catalog/region_profiles/regions_comparable.csv',flush=True)
    if any(x['status']!='ready' for x in rows):
        print('WARNING: incomplete regions must not be compared as measured values.',flush=True)

if __name__=='__main__': main()
