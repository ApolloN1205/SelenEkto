"""Input validation, clear failure messages and candidate-specific lunar solar workflow."""
from __future__ import annotations
import json
import math
from datetime import datetime, timezone
from pathlib import Path


def validate_timeline(start, hours, interval_min):
    if not isinstance(start, datetime) or start.tzinfo is None or start.utcoffset() is None:
        raise ValueError('Choose a valid UTC start date and time.')
    if not 1 <= int(hours) <= 336:
        raise ValueError('Duration must be between 1 and 336 hours.')
    if not 10 <= int(interval_min) <= 720:
        raise ValueError('Time interval must be between 10 and 720 minutes.')
    if int(hours) * 60 // int(interval_min) + 2 > 2000:
        raise ValueError('Choose a larger interval: the timeline exceeds 2,000 samples.')
    return start.astimezone(timezone.utc), int(hours), int(interval_min)


def explain_error(exc):
    raw = str(exc)
    msg = raw.lower()
    if 'no module named' in msg or isinstance(exc, ImportError):
        return 'A required Python library is missing. Run: .\\.venv\\Scripts\\python.exe -m pip install pyproj rasterio matplotlib PySide6\n\nDetails: ' + raw
    if 'http error 429' in msg or 'rate limit' in msg:
        return 'NASA JPL Horizons is limiting requests. Try a shorter interval or run again later.\n\nDetails: ' + raw
    if any(t in msg for t in ['urlopen error','timed out','name resolution','temporary failure','http error']):
        return 'Could not reach JPL Horizons. Check your internet connection and whether the service is available. No solar values were generated.\n\nDetails: ' + raw
    if any(t in msg for t in ['no such file','missing','does not exist']):
        return 'Required local NASA data is missing. Check Data Health and finish downloading the chosen region before calculating its horizon.\n\nDetails: ' + raw
    if any(t in msg for t in ['nodata','no valid elevation','nan']):
        return 'This candidate has no usable elevation at its selected cell. Select another point in Explorer.\n\nDetails: ' + raw
    if 'horizons' in msg or 'ephemeris' in msg:
        return 'JPL did not return a usable Sun-position table. Check the UTC settings and review the service response. No results were invented.\n\nDetails: ' + raw
    if 'grid' in msg or 'crs' in msg or 'projection' in msg:
        return 'The selected region has a geometry or coordinate-system issue. Check Data Health; the calculation cannot safely continue.\n\nDetails: ' + raw
    return 'The analysis could not finish. Existing saved results remain unchanged.\n\nTechnical details: ' + raw


def calculate_candidate_timeline(root:Path, candidate:dict, start:datetime, hours:int, interval_min:int, scan_m=500):
    """Recalculate candidate-specific terrain horizon and query real JPL ephemeris.

    Does not reuse Site01 reference horizon, even for Site01 candidate positions.
    Caller should run this in a worker thread to keep the interface responsive.
    """
    import numpy as np
    import rasterio
    from selenekto_v2.core import region_files, region_health
    from selenekto_data.horizon import calculate_horizon
    from selenekto_data.candidate_solar import candidate_geography, fetch_candidate_sun, evaluate_candidate, timeline_statistics
    from selenekto_data.solar import project_north_offset

    start,hours,interval_min=validate_timeline(start,hours,interval_min)
    region=str(candidate['region']);row=int(candidate['row']);col=int(candidate['col'])
    health=region_health(root,region)
    if health['status']!='ready':
        raise ValueError(f"Missing or invalid NASA data for {region}: {health['details']}")
    paths=region_files(root,region)
    with rasterio.open(paths['Elevation']) as ds:
        if not 0<=row<ds.height or not 0<=col<ds.width:
            raise ValueError(f'Candidate cell row {row}, column {col} is outside {region}.')
        dem=ds.read(1,masked=True).filled(np.nan).astype(float)
        transform=ds.transform
        wkt=ds.crs.to_wkt()
        x,y=transform*(col+0.5,row+0.5)
        elevation=float(dem[row,col])
    if not math.isfinite(elevation):
        raise ValueError(f'No valid elevation at {candidate["name"]} in {region}.')
    # Explicitly read measured counts and Z RMS; no fabricated uncertainty bands.
    with rasterio.open(paths['LOLA observations']) as ds:
        counts=ds.read(1,masked=True).filled(np.nan).astype(float)
    with rasterio.open(paths['Elevation uncertainty']) as ds:
        errors=ds.read(1,masked=True).filled(np.nan).astype(float)
    angles=calculate_horizon(dem,transform,float(x),float(y),max_distance_m=scan_m,
                             sample_step_m=10,azimuth_step_deg=1,counts=counts,errors=errors)
    if len(angles)!=360 or any(a.get('horizon_angle_deg') is None for a in angles):
        raise ValueError('Candidate horizon is incomplete, possibly because the DEM ends near this location. Choose another point or a smaller scan radius.')
    latitude,longitude=candidate_geography(wkt,float(x),float(y))
    positions,source=fetch_candidate_sun(latitude,longitude,elevation,start,hours,interval_min)
    north_offset=project_north_offset(wkt,latitude,longitude)
    rows=evaluate_candidate(positions,angles,north_offset)
    summary=timeline_statistics(rows)
    result={'analysis_type':'candidate_solar', 'candidate':{'name':candidate['name'],'region':region,'row':row,'col':col,
            'latitude_deg':latitude,'longitude_east_deg':longitude,'elevation_m':elevation},
            'settings':{'start_utc':start.isoformat(),'hours':hours,'interval_min':interval_min,
                'scan_radius_m':scan_m,'grid_north_offset_deg':north_offset},
            'source':source,'summary':summary,'records':rows,
            'limitations':['Local DEM-limited horizon; terrain beyond scan radius not modelled',
               'Moon reference-frame alignment remains preliminary',
               'Model predicts Sun-centre clearance, not verified illumination or landing safety',
               'Per-candidate horizon uncertainty band not calculated in this workflow']}
    dest=root/'data'/'processed'/'solar_v2'/region
    dest.mkdir(parents=True,exist_ok=True)
    import re
    safe_name=re.sub(r'[^A-Za-z0-9_-]+','_',str(candidate['name']))[:45].strip('_') or 'Candidate'
    stem=f'{safe_name}_{row}_{col}_{start.strftime("%Y%m%dT%H%M")}'
    file=dest/(stem+'.json')
    # Only save a complete result, and avoid overwriting previous runs.
    import tempfile, os
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=dest,suffix='.tmp',delete=False) as fh:
        tmp=Path(fh.name);json.dump(result,fh,indent=2,allow_nan=False)
    try:os.replace(tmp,file)
    finally:tmp.unlink(missing_ok=True)
    return result,file


def calculate_candidate_horizon(root: Path, candidate: dict, scan_m=500):
    """Calculate an offline horizon from this candidate's own DEM (never Site01 fallback).

    Save only after a complete 360-direction calculation. Uses the same scientific
    algorithm and scan settings as calculate_candidate_timeline().
    """
    import numpy as np
    import rasterio
    from selenekto_v2.core import region_files, region_health
    from selenekto_data.horizon import calculate_horizon

    region=str(candidate['region'])
    row=int(candidate['row']); col=int(candidate['col'])
    health=region_health(root,region)
    if health['status']!='ready':
        raise ValueError(f"Missing or invalid NASA data for {region}: {health.get('details','not ready')}")
    paths=region_files(root,region)
    with rasterio.open(paths['Elevation']) as ds:
        if not (0 <= row < ds.height and 0 <= col < ds.width):
            raise ValueError(f'Candidate ({row},{col}) lies outside {region}.')
        dem=ds.read(1,masked=True).filled(np.nan).astype(float)
        transform=ds.transform
        x,y=transform*(col+.5,row+.5)
        elevation=float(dem[row,col])
    if not math.isfinite(elevation):
        raise ValueError(f'No valid elevation at {candidate["name"]} in {region}.')
    with rasterio.open(paths['LOLA observations']) as ds:
        counts=ds.read(1,masked=True).filled(np.nan).astype(float)
    with rasterio.open(paths['Elevation uncertainty']) as ds:
        errors=ds.read(1,masked=True).filled(np.nan).astype(float)
    records=calculate_horizon(dem, transform, float(x), float(y), max_distance_m=scan_m,
                              sample_step_m=10,azimuth_step_deg=1,counts=counts,errors=errors)
    if len(records)!=360 or any(r['horizon_angle_deg'] is None for r in records):
        raise ValueError('Incomplete horizon (DEM edge or NoData). Try a different candidate.')
    result={'analysis_type':'candidate_horizon',
            'candidate':{'name':candidate['name'],'region':region,'row':row,'col':col,'elevation_m':elevation},
            'settings':{'scan_radius_m':scan_m,'azimuth_reference':'clockwise from projected grid +Y'},
            'angles':records,
            'limitations':['Local terrain within search radius only',
                           'Azimuth is projected-grid relative, not geographic north',
                           'No solar illumination or candidate-specific uncertainty band calculated']}
    dest=root/'data/processed/horizon_candidates'/region
    dest.mkdir(parents=True,exist_ok=True)
    import re, tempfile, os
    safe=re.sub(r'[^A-Za-z0-9_-]+','_',str(candidate['name']))[:45].strip('_') or 'Candidate'
    file=dest/f'{safe}_{row}_{col}_horizon.json'
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=dest,suffix='.tmp',delete=False) as fh:
        tmp=Path(fh.name);json.dump(result,fh,indent=2,allow_nan=False)
    try:os.replace(tmp,file)
    finally:tmp.unlink(missing_ok=True)
    return result,file
