"""NASA PGDA LOla south-polar data: catalogue, validation and candidate handling."""
from __future__ import annotations
from pathlib import Path
import csv, math, re

REGIONS = {
 'Site01':'Connecting ridge','Site04':'Shackleton rim','Site06':'Nobile rim 1',
 'Site07':'Peak near Shackleton','Site11':'de Gerlache rim','Site20':'Leibnitz beta plateau',
 'Site20v2':'Leibnitz beta plateau extended','Site23':'Malapert massif',
 'Site42':'de Gerlache–Kocher massif','Haworth':'Haworth','Shoemaker':'Shoemaker',
 'DM1':'Amundsen rim','DM2':'Nobile rim 2','SL2':'de Gerlache rim','SL3':'Connecting ridge extension',
 'NPA':'Cabeus exterior wall 1','NPB':'Amundsen 1','NPC':"Idel'son L crater 1",'NPD':'Malapert crater 1',
 'LM1':'Shackleton Rim B','LM2':'Shoemaker Rim A','LM3':'Shoemaker Rim B',
 'LM4':'Shoemaker Rim C','LM5':'Shoemaker Rim D','LM6':'Shoemaker Rim E',
 'LM7':'Faustini Rim A','LM8':'Shoemaker Rim F',
}
SUFFIXES = {'Elevation':'surf','Slope':'slp','Elevation uncertainty':'toterr','Slope uncertainty':'slperr','LOLA counts':'ldec'}
BASE = 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/'

def filename(region, layer):
    if region not in REGIONS or layer not in SUFFIXES:raise ValueError('Unknown NASA region or layer')
    return f'{region}_final_adj_5mpp_{SUFFIXES[layer]}.tif'

def region_files(root:Path, region):
    return {layer:root/region/filename(region,layer) for layer in SUFFIXES}

def installed_regions(root:Path):
    return [r for r in REGIONS if all(p.is_file() for p in region_files(root,r).values())]

def validate_region(root:Path, region):
    import rasterio
    files=region_files(root,region)
    missing=[k for k,p in files.items() if not p.is_file()]
    if missing:raise ValueError(f'{region} missing '+', '.join(missing))
    reference=None
    for layer,path in files.items():
        with rasterio.open(path) as ds:
            if ds.count!=1 or ds.crs is None:raise ValueError(f'Invalid raster {path}')
            properties=(ds.width,ds.height,tuple(ds.transform),str(ds.crs))
            if reference is None:reference=properties
            elif reference!=properties:raise ValueError(f'Grid registration mismatch: {layer}')
    return files

def validate_name(text):
    if not isinstance(text,str):raise ValueError('Name is not text')
    clean=' '.join(text.split())
    if not clean or len(clean)>64 or clean[0] in '=+@-':raise ValueError('Choose a 1–64 character name not starting with a spreadsheet formula symbol')
    return clean

def read_metrics(datasets,row,col):
    import numpy as np
    fields={'Elevation':'elevation_m','Slope':'slope_deg','Elevation uncertainty':'elevation_rms_m','Slope uncertainty':'slope_rms_deg','LOLA counts':'lola_spot_count'}
    out={}
    for layer,field in fields.items():
        ds=datasets.get(layer)
        if ds is None:out[field]=None;continue
        z=float(ds.read(1,window=((row,row+1),(col,col+1)))[0,0])
        out[field]=round(z,6) if np.isfinite(z) and (ds.nodata is None or z!=ds.nodata) else None
    return out

def export_candidates(path,records):
    fields=['region','name','row','col','x_projected_m','y_projected_m','elevation_m','slope_deg','elevation_rms_m','slope_rms_deg','lola_spot_count']
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(records)
    return path

def slope_comparison(records,weights):
    """Terrain-only relative preferences, not an engineering safety rating."""
    keys=['slope_deg','elevation_rms_m']
    if any(not isinstance(weights[k],(int,float)) or not math.isfinite(weights[k]) or weights[k]<0 for k in keys):raise ValueError('Invalid weights')
    if sum(weights.values())==0:raise ValueError('At least one nonzero weight required')
    if any(any(r.get(k) is None or not math.isfinite(float(r[k])) for k in keys) for r in records):raise ValueError('Missing terrain metrics')
    lo={k:min(r[k] for r in records) for k in keys};hi={k:max(r[k] for r in records) for k in keys}
    return [{**r,'terrain_preference_score':round(sum(weights[k]*(0.5 if hi[k]==lo[k] else (hi[k]-r[k])/(hi[k]-lo[k])) for k in keys)/sum(weights.values()),5)} for r in records]
