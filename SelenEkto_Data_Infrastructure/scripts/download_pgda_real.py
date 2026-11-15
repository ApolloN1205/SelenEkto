#!/usr/bin/env python3
"""Download genuine NASA PGDA Product 78 5mpp GeoTIFF layers by region.

Usage:
  python scripts/download_pgda_real.py --site Site04
  python scripts/download_pgda_real.py --all
  python scripts/download_pgda_real.py --all --verify-only

Does not overwrite existing validated GeoTIFFs. Incomplete files are discarded.
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REGIONS = ('Site01','Site04','Site06','Site07','Site11','Site20','Site20v2','Site23','Site42','Haworth','Shoemaker','DM1','DM2','SL2','SL3','NPA','NPB','NPC','NPD','LM1','LM2','LM3','LM4','LM5','LM6','LM7','LM8')
LAYERS = ('surf','slp','ldec','toterr','slperr')
BASE_URL = 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp'
ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / 'data' / 'raw' / 'lola'


def valid_tiff(path):
    if not path.is_file() or path.stat().st_size < 1024:
        return False, 'file absent or too small'
    with path.open('rb') as handle:
        magic = handle.read(4)
    if magic not in (b'II*\x00', b'MM\x00*', b'II+\x00', b'MM\x00+'):
        return False, 'not a TIFF header'
    try:
        import rasterio
        with rasterio.open(path) as ds:
            if ds.count < 1 or ds.width < 1 or ds.height < 1:
                return False, 'invalid raster dimensions'
    except ImportError:
        pass
    except Exception as exc:
        return False, 'GeoTIFF read error: '+str(exc)
    return True, 'OK'


def download_one(site, layer):
    filename = f'{site}_final_adj_5mpp_{layer}.tif'
    folder = DATA_ROOT / site
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / filename
    url = f'{BASE_URL}/{site}/{filename}'
    good, why = valid_tiff(destination)
    if good:
        print(f'  SKIP {filename} ({destination.stat().st_size:,} bytes)', flush=True)
        return True, {'file': filename, 'url': url, 'size': destination.stat().st_size, 'status':'existing_valid'}
    if destination.exists():
        print(f'  WARNING {filename}: existing file invalid ({why}); not overwriting it', flush=True)
        return False, {'file': filename, 'url': url, 'status':'invalid_existing','error':why}
    temporary = destination.with_suffix('.tif.part')
    if temporary.exists():
        temporary.unlink()  # incomplete transfer; start fresh
    request = urllib.request.Request(url, headers={'User-Agent': 'SelenEkto-Research/1.0 (NASA public data)'})
    print(f'  GET {filename}', flush=True)
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as output:
            if response.status != 200:
                raise ValueError(f'Unexpected HTTP status: {response.status}')
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
            expected_length = response.headers.get('Content-Length')
            if expected_length and int(expected_length) != total:
                raise ValueError(f'Incomplete transfer: expected {expected_length} bytes, received {total}')
        good, why = valid_tiff(temporary)
        if not good:
            raise ValueError('Downloaded file invalid: ' + why)
        os.replace(temporary, destination)
        print(f'  OK   {total:,} bytes', flush=True)
        return True, {'file': filename, 'url':url,'size':total,'sha256':digest.hexdigest(),'status':'downloaded'}
    except Exception as exc:
        if temporary.exists():
            temporary.unlink()
        print(f'  FAIL {filename}: {exc}', flush=True)
        return False, {'file':filename,'url':url,'status':'failed','error':str(exc)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--site',choices=REGIONS)
    group.add_argument('--all',action='store_true')
    parser.add_argument('--verify-only',action='store_true',help='Check local files without downloading')
    args=parser.parse_args()
    selected=REGIONS if args.all else (args.site,)
    results={}
    counts={'complete':0,'incomplete':0}
    for site in selected:
        print(f'\n[{site}]',flush=True)
        records=[]
        successes=0
        for layer in LAYERS:
            if args.verify_only:
                path=DATA_ROOT/site/f'{site}_final_adj_5mpp_{layer}.tif'
                good,why=valid_tiff(path)
                print(f'  {layer}: {"OK" if good else "MISSING / INVALID"} — {why}')
                result={'file':path.name,'status':'valid' if good else 'missing_or_invalid','detail':why}
            else:
                good,result=download_one(site,layer)
            successes+=int(good)
            records.append(result)
        complete=successes==5
        counts['complete' if complete else 'incomplete']+=1
        results[site]={'status':'ready' if complete else 'incomplete','layers_ready':successes,'layers':records}
        print(f'  STATUS {successes}/5 layers ready',flush=True)
        manifest=DATA_ROOT/site/'selenekto_download_manifest.json'
        if not args.verify_only:
            manifest.write_text(json.dumps({'source':BASE_URL,'site':site,**results[site]},indent=2)+'\n',encoding='utf-8')
    print(f'\nFINISHED: {counts["complete"]} complete, {counts["incomplete"]} incomplete',flush=True)
    return 0 if counts['incomplete']==0 else 1

if __name__=='__main__':
    sys.exit(main())
