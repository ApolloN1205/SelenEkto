"""Download up to 27 NASA PGDA terrain regions, never overwriting validated files.
Run --all to fetch all 27. Ctrl+C can stop safely and another run continues.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, time, urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.unified_regions import REGIONS,region_files,validate_region,BASE
from selenekto_data.repair_utils import pgda_url

def main():
    import rasterio
    parser=argparse.ArgumentParser(description='NASA PGDA 5m/pixel verified terrain rasters (5 per region)')
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all',action='store_true',help='Download all 27 listed regions; potentially multiple GB')
    group.add_argument('--regions',nargs='+',choices=REGIONS,help='Download specified regions')
    args=parser.parse_args()
    regions=list(REGIONS) if args.all else args.regions
    root=ROOT/'data/raw/lola';errors=[]
    for index,region in enumerate(regions,1):
        print(f'\n===== {region} ({index}/{len(regions)}): {REGIONS[region]} =====',flush=True)
        files=region_files(root,region);manifest=[]
        for layer,dest in files.items():
            dest.parent.mkdir(parents=True,exist_ok=True)
            url=pgda_url(region,dest.name)
            if dest.is_file():
                try:
                    with rasterio.open(dest) as ds:
                        if ds.count!=1 or ds.crs is None or ds.width<100:raise ValueError('invalid raster')
                    print('SKIP validated existing',dest.name,flush=True)
                    manifest.append({'layer':layer,'file':str(dest),'status':'already-present','url':url})
                    continue
                except Exception:
                    errors.append(f'{region}/{layer}: existing file invalid, manual inspection required');continue
            part=dest.with_suffix('.part')
            if part.exists():part.unlink() # partial is never considered complete
            sha=hashlib.sha256();size=0
            print('GET',url,flush=True)
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'SelenEkto educational open lunar data client'})
                with urllib.request.urlopen(req,timeout=120) as response,part.open('wb') as out:
                    while chunk:=response.read(1024*1024):
                        out.write(chunk);sha.update(chunk);size+=len(chunk)
                with rasterio.open(part) as ds:
                    if ds.count!=1 or ds.crs is None or ds.width<100 or ds.height<100:raise ValueError('Invalid downloaded raster')
                part.replace(dest)
                print('OK',round(size/1024/1024,2),'MiB',flush=True)
                manifest.append({'layer':layer,'url':url,'file':str(dest),'size_bytes':size,'sha256':sha.hexdigest(),'status':'downloaded'})
            except KeyboardInterrupt:
                if part.exists():part.unlink()
                print('Stopped by user. Existing completed TIFFs are preserved.');raise SystemExit(130)
            except Exception as exc:
                if part.exists():part.unlink()
                errors.append(f'{region}/{layer}: {exc}');print('FAILED',exc,flush=True)
        try:
            validate_region(root,region)
        except Exception as exc:
            errors.append(f'{region}: incomplete or unaligned ({exc})');continue
        manifest_path=root/region/'selenekto_download_manifest.json'
        manifest_path.write_text(json.dumps({'region':region,'source':BASE,'verified_utc':datetime.now(timezone.utc).isoformat(),'files':manifest},indent=2),encoding='utf-8')
        print('REGION READY:',region,flush=True)
    print('\nDownload finished. Issues:',len(errors))
    for issue in errors:print(' -',issue)
    if errors:raise SystemExit(1)
if __name__=='__main__':main()
