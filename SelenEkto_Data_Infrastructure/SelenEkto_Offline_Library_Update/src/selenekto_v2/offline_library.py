"""Small offline dataset catalogue for SelenEkto, with explicit on-demand NASA layers."""
from __future__ import annotations
import json
from pathlib import Path

REGIONS = ('Site01','Site04','Site06','Site07','Site11','Site20','Site20v2','Site23','Site42','Haworth','Shoemaker','DM1','DM2','SL2','SL3','NPA','NPB','NPC','NPD','LM1','LM2','LM3','LM4','LM5','LM6','LM7','LM8')
LAYERS=('surf','slp','ldec','toterr','slperr')
KNOWN_ISSUES={'LM8':'Reported incomplete; download and check missing layers', 'Site20':'Reported invalid/misaligned; do not use for analysis', 'Site23':'Reported invalid/misaligned; do not use for analysis'}

def raster_path(root,region,layer):
    if region not in REGIONS or layer not in LAYERS:
        raise ValueError('Unknown region or NASA layer')
    return Path(root)/'data'/'raw'/'lola'/region/f'{region}_final_adj_5mpp_{layer}.tif'

def preview_path(root,region):
    if region not in REGIONS: raise ValueError('Unknown region')
    return Path(root)/'data'/'catalog'/'previews'/f'{region}_elevation.png'

def catalogue_status(root,region):
    """Presence indicator only; never imply file alignment or valid science."""
    paths=[raster_path(root,region,layer) for layer in LAYERS]
    found=sum(p.is_file() and p.stat().st_size>1024 for p in paths)
    return {'region':region,'present_layers':found,'expected_layers':5,
            'preview':preview_path(root,region).is_file(),
            'warning':KNOWN_ISSUES.get(region,''),
            'note':'File count is not a raster-integrity or alignment check'}

def safe_profile(root,region):
    """Return optional profile JSON; never manufacture scientific measurements."""
    folder=Path(root)/'data'/'catalog'/'region_profiles'
    for candidate in (folder/f'{region}.json',folder/f'{region}_profile.json'):
        if candidate.is_file():
            try:
                data=json.loads(candidate.read_text(encoding='utf-8'))
                if isinstance(data,dict): return data
            except (OSError,ValueError): pass
    return {}

def generate_preview(root,region,max_side=512):
    """Downsample authoritative elevation TIFF for offline *visual reference only*."""
    import numpy as np
    import rasterio
    from rasterio.enums import Resampling
    from PIL import Image, ImageDraw
    source=raster_path(root,region,'surf')
    if not source.is_file(): raise FileNotFoundError(f'Missing elevation GeoTIFF: {source}')
    with rasterio.open(source) as ds:
        scale=max(ds.width,ds.height)/max_side
        size=(max(1,round(ds.height/max(1,scale))),max(1,round(ds.width/max(1,scale))))
        data=ds.read(1,out_shape=size,masked=True,resampling=Resampling.average)
    valid=np.asarray(data.compressed(),dtype='float64')
    valid=valid[np.isfinite(valid)]
    if not len(valid): raise ValueError(f'{region}: no valid elevation data')
    lo,hi=np.percentile(valid,[2,98]);hi=max(lo+1e-9,hi)
    arr=np.asarray(data.filled(np.nan),dtype='float64')
    grey=np.uint8(np.clip((arr-lo)/(hi-lo),0,1)*235+12)
    grey[~np.isfinite(arr)]=0
    im=Image.fromarray(grey,mode='L').convert('RGB')
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,min(im.width,300),26),fill=(11,15,22))
    d.text((8,7),f'{region}  /  ELEVATION PREVIEW',fill=(226,230,238))
    p=preview_path(root,region);p.parent.mkdir(parents=True,exist_ok=True)
    im.save(p,optimize=True)
    return p
