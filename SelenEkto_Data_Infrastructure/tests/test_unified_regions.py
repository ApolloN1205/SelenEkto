from pathlib import Path
from selenekto_data.unified_regions import REGIONS,SUFFIXES,filename,installed_regions,validate_name,slope_comparison,export_candidates
import csv,pytest

def test_catalogue():
    assert len(REGIONS)==27
    assert len(SUFFIXES)==5
    assert filename('Site04','Slope')=='Site04_final_adj_5mpp_slp.tif'

def test_catalogue_rejects_invalid():
    with pytest.raises(ValueError):filename('../Site01','Elevation')

def test_empty_install(tmp_path):assert installed_regions(tmp_path)==[]

def test_names():
    assert validate_name('  Ridge   Alpha ')=='Ridge Alpha'
    with pytest.raises(ValueError):validate_name('=SUM(1)')

def test_relative_preferences():
    data=[{'slope_deg':4,'elevation_rms_m':.2},{'slope_deg':10,'elevation_rms_m':.4}]
    out=slope_comparison(data,{'slope_deg':1,'elevation_rms_m':1})
    assert out[0]['terrain_preference_score']==1
    assert out[1]['terrain_preference_score']==0

def test_csv_quotes_and_region(tmp_path):
    dest=tmp_path/'pts.csv';export_candidates(dest,[{'region':'Site01','name':'Ridge, A','row':1,'col':2}])
    with dest.open(newline='',encoding='utf-8') as file:
        assert next(csv.DictReader(file))['name']=='Ridge, A'
