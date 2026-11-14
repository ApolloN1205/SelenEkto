from pathlib import Path
from selenekto_data.region_audit import classify_region,describe_pixel

def test_missing_files(tmp_path):
    data=classify_region(tmp_path,'SiteXX',{'Elevation':tmp_path/'not_there.tif'})
    assert data['status']=='incomplete'
    assert data['layers']['Elevation']['status']=='missing_file'

def test_invalid_file(tmp_path):
    bad=tmp_path/'bad.tif';bad.write_bytes(b'not a geotiff')
    data=classify_region(tmp_path,'X',{'Elevation':bad})
    assert data['status']=='invalid_or_misaligned'

def test_pixel_nodata_message():
    s=describe_pixel({'elevation_m':42,'slope_deg':None})
    assert 'slope_deg' in s and 'not a zero' in s

def test_ready_raster_and_sampled_nodata(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    path=tmp_path/'elevation.tif'
    arr=np.ones((16,16),dtype='float32')
    with rasterio.open(path,'w',driver='GTiff',width=16,height=16,count=1,
                       dtype='float32',crs='EPSG:4326',transform=from_origin(0,16,1,1),nodata=-9999) as out:
        out.write(arr,1)
    result=classify_region(tmp_path,'X',{'Elevation':path})
    assert result['status']=='ready'
    assert result['layers']['Elevation']['sampled_missing_percent']==0.0
    with rasterio.open(path,'r+') as ds:
        ds.write(np.full((16,16),-9999,dtype='float32'),1)
    result=classify_region(tmp_path,'X',{'Elevation':path})
    assert result['status']=='sample_has_no_data'


def test_mismatched_grids(tmp_path):
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    for name,xorigin in [('a',0),('b',1)]:
        with rasterio.open(tmp_path/f'{name}.tif','w',driver='GTiff',width=16,height=16,count=1,
                           dtype='float32',crs='EPSG:4326',transform=from_origin(xorigin,16,1,1)) as out:
            out.write(np.ones((16,16),dtype='float32'),1)
    result=classify_region(tmp_path,'X',{'Elevation':tmp_path/'a.tif','Slope':tmp_path/'b.tif'})
    assert result['status']=='invalid_or_misaligned'
    assert result['layers']['Slope']['status']=='grid_mismatch'
