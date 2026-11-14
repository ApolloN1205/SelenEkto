"""Download ORIGINAL NASA LOLA site rasters; stream, resume-by-skip, never overwrite."""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.multiregion import SITE_NAMES,SUFFIXES,region_paths,validate_grid
BASE='https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/'


def download(region:str, root:Path, overwrite:bool=False):
    import rasterio
    paths=region_paths(root,region)
    results=[]
    for layer,path in paths.items():
        url=BASE+path.name
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists() and not overwrite:
            print(f'EXISTS: {path.name} (not overwritten)',flush=True)
            results.append({'layer':layer,'file':str(path),'status':'existing'})
            continue
        partial=path.with_suffix('.tif.part')
        if partial.exists():partial.unlink() # partial files are not valid input; restart download
        print('Downloading:',url,flush=True)
        digest=hashlib.sha256();total=0
        try:
            req=urllib.request.Request(url,headers={'User-Agent':'SelenEkto educational lunar data navigator/1.0'})
            with urllib.request.urlopen(req,timeout=75) as response,partial.open('wb') as out:
                while chunk:=response.read(1024*1024):
                    digest.update(chunk);total+=len(chunk);out.write(chunk)
            if total<4096:raise ValueError('Unexpectedly small download')
            with rasterio.open(partial) as ds:
                if ds.count!=1 or ds.width<100 or ds.height<100 or ds.crs is None:
                    raise ValueError('Downloaded file is not a valid georeferenced raster')
            partial.replace(path)
        except Exception:
            if partial.exists():partial.unlink()
            raise
        print(f'  OK {total:,} bytes SHA256 {digest.hexdigest()}',flush=True)
        results.append({'layer':layer,'file':str(path),'source_url':url,'bytes':total,'sha256':digest.hexdigest(),'status':'downloaded'})
    validate_grid(rasterio,paths)
    log=root/region/'selenekto_download_manifest.json'
    log.write_text(json.dumps({'region':region,'source':BASE,'checked_utc':datetime.now(timezone.utc).isoformat(),
                               'products':results},indent=2),encoding='utf-8')
    print('SUCCESS: all five layers present; grid geometry matched. Manifest:',log)


def main():
    parser=argparse.ArgumentParser(description='Download original high-resolution LOLA 5mpp NASA terrain layers')
    parser.add_argument('--region',choices=sorted(SITE_NAMES),required=True)
    args=parser.parse_args()
    download(args.region,ROOT/'data/raw/lola')

if __name__=='__main__':main()
