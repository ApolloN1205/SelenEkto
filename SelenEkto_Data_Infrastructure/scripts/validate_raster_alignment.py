#!/usr/bin/env python3
"""Non-destructive raster integrity/alignment screening for SelenEkto.

Checks *only included regions*; does not claim validated lunar geodesy, reference
coordinates, solar ephemerides or landing safety. Uses small representative samples
rather than reading all GB of raster data into memory.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

LAYER_CODES = {'Elevation':'surf','Slope':'slp','LOLA count':'ldec',
               'Elevation RMS':'toterr','Slope RMS':'slperr'}
REGIONS=('Site01','Site04','Site06','Site07','Site11','Site20v2','Site42',
         'Haworth','Shoemaker','DM1','DM2','SL2','SL3','NPA','NPB','NPC','NPD',
         'LM1','LM2','LM3','LM4','LM5','LM6','LM7')


def raster_for(root, region, suffix):
    folder = root/'data'/'raw'/'lola'/region
    expected=f'{region}_final_adj_5mpp_{suffix}.tif'
    direct=folder/expected
    if direct.is_file():return direct
    # No filenames from other sites; nested downloads are allowed.
    options=list((root/'data'/'raw'/'lola').glob(f'**/{expected}'))
    return options[0] if len(options)==1 else None


def validate(root:Path):
    try:
        import rasterio
        import numpy as np
        from rasterio.windows import Window
    except ImportError as exc:
        raise RuntimeError('Required for raster screening: pip install rasterio numpy') from exc
    results=[]
    for region in REGIONS:
        found={name:raster_for(root,region,suffix) for name,suffix in LAYER_CODES.items()}
        missing=[name for name,path in found.items() if path is None]
        item={'region':region,'status':'ready_for_further_validation','missing_layers':missing,'issues':[]}
        if missing:
            item['status']='incomplete'
            results.append(item)
            print(f'{region}: INCOMPLETE — {", ".join(missing)}',flush=True)
            continue
        reference=None
        for name,path in found.items():
            try:
                with rasterio.open(path) as ds:
                    if ds.count !=1 or ds.width<=0 or ds.height<=0:
                        item['issues'].append(f'{name}: invalid band/dimensions')
                        continue
                    identity=(ds.width,ds.height,ds.crs,tuple(ds.transform))
                    if reference is None: reference=identity
                    elif reference!=identity:
                        item['issues'].append(f'{name}: raster grid/CRS/transform does not match Elevation layer')
                    if ds.crs is None:item['issues'].append(f'{name}: missing CRS')
                    windows=[Window(max(0,ds.width//2-64),max(0,ds.height//2-64),
                                    min(128,ds.width),min(128,ds.height)),
                             Window(0,0,min(128,ds.width),min(128,ds.height))]
                    for w in windows:
                        block=ds.read(1,window=w,masked=True)
                        values=np.asarray(block.compressed(),dtype='float64')
                        values=values[np.isfinite(values)]
                        if not values.size:continue
                        if name in ('Slope','Slope RMS') and (values.min() < -0.001 or values.max()>90.001):
                            item['issues'].append(f'{name}: sampled value outside 0–90 degrees')
                        if name=='LOLA count' and values.min() < 0:
                            item['issues'].append('LOLA measurement count: sampled negative value')
                        if name=='Elevation RMS' and values.min() < 0:
                            item['issues'].append('Elevation RMS: sampled negative uncertainty')
            except Exception as exc:
                item['issues'].append(f'{name}: failed to open/read raster: {type(exc).__name__}: {exc}')
        if item['issues']:item['status']='invalid_or_misaligned'
        print(f'{region}: {item["status"]}'+(f' — {"; ".join(item["issues"])}' if item['issues'] else ''),flush=True)
        results.append(item)
    return {'created_utc':datetime.now(timezone.utc).isoformat(),
            'included_regions_checked':len(REGIONS),
            'excluded_from_release':['LM8','Site20','Site23'],
            'results':results,
            'all_included_complete_and_grid_aligned':all(x['status']=='ready_for_further_validation' for x in results),
            'scope_warning':('Raster metadata, alignment, and sampled value ranges only. '
                             'No independent validation of lunar coordinates, horizon, JPL ephemerides, '
                             'illuminance predictions, or actual landing suitability.')}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--strict',action='store_true',help='Return nonzero when any included region is incomplete or misaligned')
    a=p.parse_args()
    result=validate(a.root.resolve())
    report=a.root/'data'/'processed'/'release'/'raster_alignment_screen.json'
    report.parent.mkdir(parents=True,exist_ok=True)
    report.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Raster audit saved:',report)
    print('Validated grids:',sum(x['status']=='ready_for_further_validation' for x in result['results']), '/',len(REGIONS))
    print('WARNING:',result['scope_warning'])
    if a.strict and not result['all_included_complete_and_grid_aligned']:
        return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
