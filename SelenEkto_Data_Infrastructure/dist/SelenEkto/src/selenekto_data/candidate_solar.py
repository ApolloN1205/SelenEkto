"""Independent, experimental Sun/horizon evaluation for selected lunar cells."""
from __future__ import annotations
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def candidate_geography(crs_wkt, x, y):
    """Invert the local projected Moon CRS into east-positive lon/latitude."""
    from pyproj import CRS, Transformer
    geo = CRS.from_proj4('+proj=longlat +R=1737400 +no_defs +type=crs')
    target = CRS.from_wkt(crs_wkt)
    lon, lat = Transformer.from_crs(target, geo, always_xy=True).transform(x, y)
    if not (-90 <= lat <= 90 and -360 <= lon <= 360 and all(map(math.isfinite,(lon,lat)))):
        raise ValueError('Unable to convert candidate DEM coordinates to lunar longitude/latitude')
    return lat, ((lon + 180) % 360) - 180


def fetch_candidate_sun(lat, lon, elev, start, hours, interval, transport=None):
    """Request candidate-specific Horizons ephemeris; no centre-site fallback."""
    from selenekto_data.solar import horizons_parameters, parse_horizons_csv_table, HORIZONS_URL
    params = horizons_parameters(start, hours, interval, latitude=lat, longitude_east=lon, elevation_m=elev)
    url = HORIZONS_URL + '?' + urllib.parse.urlencode(params)
    if transport is None:
        def transport(address):
            request = urllib.request.Request(address, headers={'User-Agent':'SelenEkto research prototype/0.3'})
            with urllib.request.urlopen(request, timeout=45) as r:
                return r.read().decode('utf-8')
    response = json.loads(transport(url))
    if 'result' not in response:
        raise ValueError('Horizons API did not provide a result: '+str(response)[:240])
    positions = parse_horizons_csv_table(response['result'])
    return positions, {'provider':'NASA/JPL Horizons','query_parameters':params,'endpoint':HORIZONS_URL}


def evaluate_candidate(positions, horizon_records, offset_deg):
    """Align local-north Sun azimuth to grid-north and classify centre of Sun.

    No uncertainty bands are assigned unless they are separately calculated for
    the given candidate. This does not label terrain visibility as landing safety.
    """
    from selenekto_data.visibility import classify_sky_position
    pairs = sorted((float(r['grid_azimuth_deg']),float(r['horizon_angle_deg']))
                   for r in horizon_records if r.get('horizon_angle_deg') is not None)
    if len(pairs) < 2 or len(pairs) != len(horizon_records):
        raise ValueError('Incomplete per-candidate horizon: cannot evaluate timeline')
    output=[]
    for p in positions:
        azimuth=(float(p['north_azimuth_deg'])+offset_deg)%360
        result=classify_sky_position(pairs,None,azimuth,p['altitude_deg'])
        clearance=p['altitude_deg'] - result['baseline_horizon_deg']
        output.append({**p, **result,'grid_azimuth_deg':azimuth,
                       'clearance_deg':round(clearance,6),
                       'sun_centre_clear_baseline':clearance>0})
    return output


def timeline_statistics(rows):
    if not rows:
        raise ValueError('Empty timeline')
    clear=sum(r['sun_centre_clear_baseline'] for r in rows)
    return {'sample_count':len(rows),'clear_samples':clear,
            'clear_sample_fraction':round(clear/len(rows),6),
            'minimum_clearance_deg':round(min(r['clearance_deg'] for r in rows),5),
            'maximum_clearance_deg':round(max(r['clearance_deg'] for r in rows),5)}


def normalized_scores(metrics, weights):
    """User-adjustable transparent comparison; no compulsory winner.

    Metrics: illumination fraction (larger better), slope_deg and
    elevation_rms_m (smaller better). Min-max among supplied candidates.
    A constant column is neutral (0.5); it cannot differentiate candidates.
    """
    keys=('clear_sample_fraction','slope_deg','elevation_rms_m')
    if not metrics:
        raise ValueError('No candidates')
    if any(k not in weights or not math.isfinite(float(weights[k])) or weights[k]<0 for k in keys):
        raise ValueError('Weights must be nonnegative finite values for all metrics')
    if not sum(weights[k] for k in keys)>0:
        raise ValueError('At least one weight must be positive')
    for row in metrics:
        if any(k not in row or not math.isfinite(float(row[k])) for k in keys):
            raise ValueError('Every candidate must have valid comparable metrics')
    minima={k:min(float(r[k]) for r in metrics) for k in keys}
    maxima={k:max(float(r[k]) for r in metrics) for k in keys}
    output=[]
    for row in metrics:
        parts={}
        for k in keys:
            delta=maxima[k]-minima[k]
            parts[k] = .5 if delta==0 else ((float(row[k])-minima[k])/delta if k=='clear_sample_fraction' else (maxima[k]-float(row[k]))/delta)
        score=sum(parts[k]*float(weights[k]) for k in keys)/sum(weights.values())
        output.append({**row,'components_normalized':parts,'weighted_score':round(score,5)})
    return output
