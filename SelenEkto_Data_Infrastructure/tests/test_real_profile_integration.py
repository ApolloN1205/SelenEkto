from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
import rasterio
from rasterio.transform import from_origin
from selenekto_v2.actual_regions import profile_region
from selenekto_v2.core import read_cell, region_health

def test_nested_real_rasters_profile_and_candidate(tmp_path):
    raw=tmp_path/'data/raw/lola'; nested=raw/'Site04'/'subfolder';nested.mkdir(parents=True)
    names={'surf':100,'slp':10,'toterr':0.5,'slperr':1.1,'ldec':3}
    for suffix,value in names.items():
        dest=nested/f'Site04_final_adj_5mpp_{suffix}.tif'
        with rasterio.open(dest,'w',driver='GTiff',height=4,width=4,count=1,dtype='float32',
                           crs='+proj=stere +lat_0=-90 +lon_0=0 +R=1737400 +units=m',
                           transform=from_origin(0,20,5,5)) as ds:
            ds.write(np.full((4,4),value,dtype='float32'),1)
    data=profile_region(raw,'Site04')
    assert data['availability']=='ready',data['errors']
    assert data['layers']['slope']['statistics']['mean']==10
    assert data['layers']['measurement_count']['statistics']['pixels_with_at_least_one_spot_percent']==100
    assert region_health(tmp_path,'Site04')['status']=='ready'
    cell=read_cell(tmp_path,'Site04',0,0)
    assert cell['slope_deg']==10 and cell['lola_spot_count']==3
