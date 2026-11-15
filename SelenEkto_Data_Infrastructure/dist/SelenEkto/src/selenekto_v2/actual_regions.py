"""Real five-layer NASA terrain profiles and candidate-cell refresh.

Profiles are raster-derived summaries, NOT substitutes for the original TIFF cells.
Never fill missing values with zeros or values borrowed from Site01.
"""
from __future__ import annotations
import csv
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SUFFIX = {'elevation': 'surf', 'slope': 'slp', 'elevation_uncertainty': 'toterr',
          'slope_uncertainty': 'slperr', 'measurement_count': 'ldec'}
UNITS = {'elevation': 'm', 'slope': 'degrees', 'elevation_uncertainty': 'RMS m',
         'slope_uncertainty': 'RMS degrees', 'measurement_count': 'LOLA spots / pixel'}
CANDIDATE = {'elevation': 'elevation_m', 'slope': 'slope_deg', 'elevation_uncertainty': 'elevation_rms_m',
             'slope_uncertainty': 'slope_rms_deg', 'measurement_count': 'lola_spot_count'}


def atomic_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent, suffix='.tmp', delete=False) as f:
        temp=Path(f.name)
        json.dump(payload, f, indent=2, ensure_ascii=False, allow_nan=False)
    try: os.replace(temp, path)
    finally: temp.unlink(missing_ok=True)


def find_rasters(raw: Path, region: str) -> dict:
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


def source_regions(raw: Path) -> list[str]:
    if not raw.is_dir():return []
    names=set()
    for p in raw.rglob('*_final_adj_5mpp_*.tif'):
        code=p.name.split('_final_adj_5mpp_')[0]
        if code.isalnum():names.add(code)
    return sorted(names)


def profile_region(raw: Path, region: str, display_name: str = '') -> dict:
    import rasterio
    from selenekto_data.region_profiles import finite_statistics
    files=find_rasters(raw,region)
    output={'schema_version':'3.0','report_type':'selenekto_site_terrain_profile',
            'site_code':region,'region_name':display_name or region,
            'generated_utc':datetime.now(timezone.utc).isoformat(),
            'source':'NASA/GSFC PGDA LOLA 5mpp (local original GeoTIFFs)',
            'availability':'incomplete', 'grid':None,'layers':{},'readable_metrics':{},
            'dataset_provenance':[], 'errors':[],
            'notes':['Each layer is recalculated from its own local raster.',
                     'Valid counts, mean, min, max and population standard deviation use all valid raster pixels.',
                     'Median and percentiles are sampled estimates, not exact full-raster statistics.',
                     'Zero LOLA spots is a valid count, not missing data.',
                     'A region-average slope does not describe a particular candidate pixel.',
                     'NoData stays null. No other region is used to fill missing pixels.']}
    reference=None
    for layer, suffix in SUFFIX.items():
        path=files[layer]
        entry={'status':'missing_file','source_file':f'{region}_final_adj_5mpp_{suffix}.tif',
               'units':UNITS[layer], 'statistics':None}
        if path is None:
            output['errors'].append(f'{layer}: missing or ambiguously located GeoTIFF')
        else:
            try:
                with rasterio.open(path) as ds:
                    if ds.count!=1 or not ds.crs or ds.width<1 or ds.height<1:
                        raise ValueError('Expected a single-band, georeferenced raster')
                    geom=(ds.width,ds.height,tuple(ds.transform),ds.crs.to_wkt())
                    if reference is None:
                        reference=geom
                        output['grid']={'width':ds.width,'height':ds.height,
                           'pixel_count':ds.width*ds.height,'transform':list(ds.transform)[:6],
                           'crs_wkt':ds.crs.to_wkt(),'bounds':list(ds.bounds),
                           'resolution_xy_m':[abs(ds.transform.a),abs(ds.transform.e)],
                           'all_five_layers_match':False}
                    if reference!=geom:
                        entry['status']='grid_mismatch'
                        output['errors'].append(f'{layer}: grid differs from first available layer')
                    else:
                        stats=finite_statistics(ds, measurement_count=(layer=='measurement_count'))
                        entry['statistics']=stats
                        entry['status']='ready' if stats['valid_pixels'] else 'all_nodata'
                        if not stats['valid_pixels']:
                            output['errors'].append(f'{layer}: all pixels NoData')
                        output['dataset_provenance'].append({'layer':layer,'path':str(path),
                            'file_size_bytes':path.stat().st_size})
            except Exception as exc:
                entry['status']='invalid_file'
                output['errors'].append(f'{layer}: {type(exc).__name__}: {str(exc)[:180]}')
        output['layers'][layer]=entry
        st=entry['statistics'] or {}
        output['readable_metrics'][layer]={
            'status':entry['status'],'units':UNITS[layer],
            'minimum':st.get('minimum'),'maximum':st.get('maximum'),
            'mean':st.get('mean'),'median':st.get('median'),
            'standard_deviation':st.get('standard_deviation_population'),
            'valid_pixels':st.get('valid_pixels'),'valid_coverage_percent':st.get('valid_coverage_percent'),
            'median_is_approximate':True,
        }
        if layer=='measurement_count':
            output['readable_metrics'][layer]['pixels_with_at_least_one_spot_percent']=st.get('pixels_with_at_least_one_spot_percent')
            output['readable_metrics'][layer]['spot_count_distribution']=st.get('spot_count_distribution')
    statuses=[v['status'] for v in output['layers'].values()]
    if all(s=='ready' for s in statuses):
        output['availability']='ready'
        output['grid']['all_five_layers_match']=True
    elif any(s in ('invalid_file','grid_mismatch') for s in statuses):output['availability']='invalid_or_misaligned'
    elif 'all_nodata' in statuses:output['availability']='contains_all_nodata_layer'
    return output


def regenerate(raw: Path, profiles: Path, names: dict[str,str], *, write=True):
    rows=[]
    for index,(code,name) in enumerate(names.items(),1):
        print(f'[{index}/{len(names)}] {code}: reading actual NASA rasters',flush=True)
        prof=profile_region(raw,code,name)
        if write: atomic_json(profiles/f'{code}_terrain_profile.json',prof)
        metrics=prof['readable_metrics']
        row={'region':code,'name':name,'status':prof['availability'],
             'ready_layers':sum(e['status']=='ready' for e in prof['layers'].values()),
             'mean_elevation_m':metrics['elevation']['mean'],
             'mean_slope_deg':metrics['slope']['mean'],
             'mean_elevation_uncertainty_rms_m':metrics['elevation_uncertainty']['mean'],
             'mean_slope_uncertainty_rms_deg':metrics['slope_uncertainty']['mean'],
             'direct_lola_coverage_percent':metrics['measurement_count'].get('pixels_with_at_least_one_spot_percent'),
             'errors':' | '.join(prof['errors'])}
        rows.append(row)
        print(f"    {row['status']} — {row['ready_layers']}/5 valid layers; slope mean: {row['mean_slope_deg']}",flush=True)
    if write:
        profiles.mkdir(parents=True,exist_ok=True)
        with (profiles/'regions_comparable.csv').open('w',newline='',encoding='utf-8-sig') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]) if rows else ['region','status'])
            writer.writeheader();writer.writerows(rows)
        atomic_json(profiles/'regions_index.json',{
            'schema_version':'3.0', 'total_regions':len(rows),
            'ready_regions':sum(r['status']=='ready' for r in rows),
            'regions':[{'site_code':r['region'],'region_name':r['name'],
                        'status':r['status'],'file':r['region']+'_terrain_profile.json',
                        'errors':r['errors']} for r in rows]})
    return rows


def refresh_saved_candidates(root:Path, *, write=True):
    """Re-read named candidates from original raster cell; preserve name/coordinates and old file on failures."""
    from selenekto_v2.core import load_candidates, save_candidates, read_cell
    path=root/'data/catalog/named_candidates.json'
    if not path.exists():return {'count':0,'updated':0,'unavailable':0,'errors':[],'message':'No saved candidates yet'}
    records=load_candidates(root); errors=[];updated=0
    for r in records:
        try:
            actual=read_cell(root,r['region'],r['row'],r['col'])
            for fld in CANDIDATE.values():r[fld]=actual.get(fld)
            for fld in ('x_projected_m','y_projected_m'):
                if fld in actual:r[fld]=actual[fld]
            updated+=1
        except Exception as exc:
            # Avoid keeping older measurements that might describe a different raster version.
            for fld in CANDIDATE.values():r[fld]=None
            errors.append(f"{r['name']} ({r['region']}): {type(exc).__name__}: {exc}")
    if write:
        backup=path.with_name('named_candidates.before_raster_refresh.json')
        if not backup.exists():backup.write_bytes(path.read_bytes())
        save_candidates(root,records)
    return {'count':len(records),'updated':updated,'unavailable':len(errors),'errors':errors}
