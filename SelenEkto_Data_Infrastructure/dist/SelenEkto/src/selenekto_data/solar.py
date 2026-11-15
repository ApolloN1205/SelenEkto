"""Experimental lunar Sun ephemeris integration for SelenEkto.

Ephemerides come from JPL Horizons over HTTPS, never estimated locally.
A projection-based bearing conversion maps Horizons local-north azimuths to
our PGDA DEM's +Y clockwise grid convention. Requires rasterio/pyproj.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

HORIZONS_URL = 'https://ssd.jpl.nasa.gov/api/horizons.api'
SITE_LAT = -89.4632
SITE_LON_EAST = -137.49
SITE_ELEVATION_M = 1944.632568359375
STAMP_RE = re.compile(r'^\s*(\d{4}-[A-Za-z]{3}-\d{2}\s+\d{2}:\d{2}(?::\d{2})?)\s*,(.*)$')
DECIMAL_RE = re.compile(r'^[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?$')


def parse_horizons_csv_table(raw):
    """Read Horizons' QUANTITIES=4, CSV_FORMAT=YES observer records.

    Intentionally fails closed if the service changes output format.
    """
    if '$$SOE' not in raw or '$$EOE' not in raw:
        raise ValueError('Horizons did not return an ephemeris table; see service message: ' + raw[:400].replace('\n', ' '))
    table = raw.split('$$SOE', 1)[1].split('$$EOE', 1)[0]
    results = []
    for line in table.splitlines():
        if not line.strip():
            continue
        match = STAMP_RE.match(line)
        if not match:
            raise ValueError('Unrecognised Horizons CSV row: ' + line[:160])
        timestamp = match.group(1)
        parts = next(csv.reader([match.group(2)], skipinitialspace=True))
        # QUANTITIES=4 returns only azimuth and elevation numerics, along with
        # optional blank/solar markers. Fail if we do not find exactly two.
        numbers = [float(t.strip()) for t in parts if DECIMAL_RE.fullmatch(t.strip())]
        if len(numbers) != 2:
            raise ValueError('Expected precisely two Horizons azimuth/elevation values: ' + line[:160])
        azimuth, altitude = numbers
        if not (0 <= azimuth <= 360 and -90 <= altitude <= 90):
            raise ValueError('Horizons solar azimuth/elevation outside physical range')
        fmt = '%Y-%b-%d %H:%M:%S' if len(timestamp.split(':')) == 3 else '%Y-%b-%d %H:%M'
        utc = datetime.strptime(timestamp, fmt).replace(tzinfo=timezone.utc)
        results.append({'timestamp_utc': utc.isoformat().replace('+00:00', 'Z'),
                        'north_azimuth_deg': azimuth, 'altitude_deg': altitude})
    if not results:
        raise ValueError('Horizons returned an empty ephemeris table')
    return results


def horizons_parameters(start_utc, hours=72, step_minutes=60,
                        latitude=SITE_LAT, longitude_east=SITE_LON_EAST,
                        elevation_m=SITE_ELEVATION_M):
    if start_utc.tzinfo is None or start_utc.utcoffset() is None:
        raise ValueError('Start time must have a timezone')
    if not (1 <= int(hours) <= 336 and 10 <= int(step_minutes) <= 720):
        raise ValueError('Supported timeline: 1–336 hours, 10–720 min step')
    if (int(hours)*60 // int(step_minutes)) + 2 > 2000:
        raise ValueError('Too many timeline samples')
    if not (-90 <= latitude <= 90 and -360 <= longitude_east <= 360 and math.isfinite(elevation_m)):
        raise ValueError('Invalid site coordinates')
    start = start_utc.astimezone(timezone.utc).replace(second=0, microsecond=0)
    stop = start + timedelta(hours=int(hours))
    quote = lambda s: "'" + str(s) + "'"
    return {'format':'json', 'COMMAND':quote('10'), 'OBJ_DATA':quote('NO'),
            'MAKE_EPHEM':quote('YES'), 'EPHEM_TYPE':quote('OBSERVER'),
            'CENTER':quote('coord@301'), 'COORD_TYPE':quote('GEODETIC'),
            'SITE_COORD':quote(f'{longitude_east:.8f},{latitude:.8f},{elevation_m/1000:.8f}'),
            'START_TIME':quote(start.strftime('%Y-%m-%d %H:%M')),
            'STOP_TIME':quote(stop.strftime('%Y-%m-%d %H:%M')),
            'STEP_SIZE':quote(f'{int(step_minutes)}m'), 'QUANTITIES':quote('4'),
            'CSV_FORMAT':quote('YES'), 'TIME_TYPE':quote('UT'),
            'TIME_DIGITS':quote('MINUTES'), 'APPARENT':quote('AIRLESS'),
            'ELEV_CUT':quote('-90'), 'SKIP_DAYLT':quote('NO')}


def fetch_sun_positions(start_utc, hours=72, step_minutes=60, timeout=40, transport=None):
    """Return observations and request metadata. Internet connection required."""
    params = horizons_parameters(start_utc, hours, step_minutes)
    encoded = urllib.parse.urlencode(params)
    url = HORIZONS_URL + '?' + encoded
    if transport is None:
        def transport(address):
            req = urllib.request.Request(address, headers={'User-Agent':'SelenEkto student research app/0.2'})
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read().decode('utf-8')
    payload = json.loads(transport(url))
    if 'result' not in payload:
        raise ValueError('Unexpected JPL Horizons API response: ' + str(payload)[:200])
    positions = parse_horizons_csv_table(payload['result'])
    return positions, {'provider':'NASA/JPL Horizons','api_url':HORIZONS_URL,
                       'query_parameters':params, 'returned_records':len(positions),
                       'disclaimer':'Solar positions from Horizons; terrain obstruction remains experimental.'}


def project_north_offset(raster_crs_wkt, latitude=SITE_LAT, longitude_east=SITE_LON_EAST, span_m=20):
    """Local grid azimuth of geographic north, using a spherical Moon finite difference.

    This tests grid projection orientation, NOT precise MOON_ME frame alignment.
    """
    from pyproj import CRS, Geod, Transformer
    moon_geo = CRS.from_proj4('+proj=longlat +R=1737400 +no_defs +type=crs')
    target = CRS.from_wkt(raster_crs_wkt)
    projection = Transformer.from_crs(moon_geo, target, always_xy=True)
    geod = Geod(a=1737400, b=1737400)
    lon_n, lat_n, _ = geod.fwd(longitude_east, latitude, 0, span_m)
    x0, y0 = projection.transform(longitude_east, latitude)
    x1, y1 = projection.transform(lon_n, lat_n)
    dx, dy = x1-x0, y1-y0
    if not (math.isfinite(dx) and math.isfinite(dy)) or math.hypot(dx,dy)<0.001:
        raise ValueError('Cannot determine projected north orientation')
    return math.degrees(math.atan2(dx, dy)) % 360


def convert_to_grid(positions, grid_north_offset_deg):
    return [{**p,'grid_azimuth_deg':(p['north_azimuth_deg'] + grid_north_offset_deg)%360}
            for p in positions]


def evaluate_solar_timeline(positions, horizon, uncertainty):
    from selenekto_data.visibility import classify_sky_position
    if not positions:
        raise ValueError('No Sun positions')
    rows=[]
    for p in positions:
        r=classify_sky_position(horizon,uncertainty,p['grid_azimuth_deg'],p['altitude_deg'])
        margin = p['altitude_deg'] - r['baseline_horizon_deg']
        rows.append({**p,**r,'baseline_clearance_deg':round(margin,5)})
    return rows


def save_solar_results(rows, metadata, output_folder):
    output=Path(output_folder)
    output.mkdir(parents=True,exist_ok=True)
    json_path = output/'Site01_solar_timeline.json'
    csv_path = output/'Site01_solar_timeline.csv'
    with json_path.open('w', encoding='utf-8') as file:
        json.dump({'metadata':metadata,'records':rows},file,indent=2)
    with csv_path.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    return json_path,csv_path
