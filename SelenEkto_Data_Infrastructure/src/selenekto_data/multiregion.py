"""Region discovery, strict naming and non-overwriting candidate storage.

Data source: https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/
Only actual locally installed rasters are offered. No manufactured terrain data.
"""
from __future__ import annotations
import csv
import json
import re
from pathlib import Path

SITE_NAMES = {
 'Site01':'Connecting Ridge','Site04':'Shackleton rim','Site07':'Peak near Shackleton',
 'Site11':'de Gerlache rim','Site20':'Leibnitz beta plateau','Site23':'Malapert massif',
}
SUFFIXES = {'Elevation':'surf','Slope':'slp','Elevation uncertainty':'toterr',
            'Slope uncertainty':'slperr','LOLA counts':'ldec'}
REGION_ID = re.compile(r'^Site(?:01|04|07|11|20|23)$')


def region_paths(raw:Path, region:str):
    if not REGION_ID.fullmatch(region):
        raise ValueError('Unsupported region ID for the six-site LOLA dataset')
    return {key: raw/region/f'{region}_final_adj_5mpp_{suffix}.tif'
            for key,suffix in SUFFIXES.items()}


def discover(raw:Path):
    output=[]
    for region in SITE_NAMES:
        files=region_paths(raw,region)
        if files['Elevation'].is_file() and files['Slope'].is_file():
            output.append({'id':region,'name':SITE_NAMES[region],
                           'complete':all(p.is_file() for p in files.values()),
                           'available_layers':[k for k,p in files.items() if p.is_file()]})
    return output


def validate_grid(rasterio, paths):
    """Ensure every present raster is registered to the same grid geometry."""
    reference=None
    for layer,path in paths.items():
        if not path.is_file():continue
        with rasterio.open(path) as ds:
            grid=(ds.width,ds.height,tuple(ds.transform),str(ds.crs))
            if reference is None:reference=grid
            elif grid!=reference:raise ValueError(f'Grid mismatch in {layer}: {path}')
    if reference is None:raise ValueError('No rasters found')
    return reference


def normalize_candidate_name(value:str):
    """Clean human-readable labels, preventing blank and spreadsheet-formula names."""
    if not isinstance(value, str):
        raise ValueError('Candidate name must be text')
    name=' '.join(value.split())
    if not 1 <= len(name) <= 64:
        raise ValueError('Candidate name must be 1–64 characters')
    if name[0] in '=+@-':
        raise ValueError('Candidate name must not begin with a spreadsheet formula prefix')
    if any(ord(ch)<32 for ch in name):
        raise ValueError('Candidate name contains an unsupported control character')
    return name


def rename_candidate(candidates:list, index:int, new_name:str):
    if not 0 <= index < len(candidates):
        raise IndexError('No candidate selected')
    label=normalize_candidate_name(new_name)
    region=candidates[index]['region']
    if any(i != index and c['region']==region and c['name'].casefold()==label.casefold()
           for i,c in enumerate(candidates)):
        raise ValueError('A candidate in this region already has that name')
    candidates[index]['name']=label
    return candidates[index]


def safe_candidate_record(region:str, name:str, row:int, col:int, x:float, y:float, metrics:dict):
    if region not in SITE_NAMES:raise ValueError('Unknown region')
    if row<0 or col<0:raise ValueError('Invalid cell')
    return {'region':region,'name':name,'row':int(row),'col':int(col),
            'x_projected_m':float(x),'y_projected_m':float(y),**metrics}


def export_candidates(path:Path, candidates:list):
    if not candidates:raise ValueError('Select at least one candidate')
    path.parent.mkdir(parents=True,exist_ok=True)
    fields=['region','name','row','col','x_projected_m','y_projected_m',
            'elevation_m','slope_deg','elevation_rms_m','slope_rms_deg','lola_spot_count']
    with path.open('w',newline='',encoding='utf-8') as file:
        writer=csv.DictWriter(file,fieldnames=fields,extrasaction='ignore')
        writer.writeheader();writer.writerows(candidates)
    return path


def record_metrics(layers:dict, row:int,col:int):
    """Read one original raster cell per supplied layer; missing values stay None."""
    import math
    fieldmap={'Elevation':'elevation_m','Slope':'slope_deg',
              'Elevation uncertainty':'elevation_rms_m',
              'Slope uncertainty':'slope_rms_deg','LOLA counts':'lola_spot_count'}
    result={}
    for layer,key in fieldmap.items():
        ds=layers.get(layer)
        if ds is None:result[key]=None;continue
        value=float(ds.read(1,window=((row,row+1),(col,col+1)))[0,0])
        result[key]=round(value,6) if math.isfinite(value) and (ds.nodata is None or value!=ds.nodata) else None
    return result
