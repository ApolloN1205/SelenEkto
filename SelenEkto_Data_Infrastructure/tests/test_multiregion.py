from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from selenekto_data.multiregion import normalize_candidate_name,rename_candidate,export_candidates,region_paths,discover

def test_name_cleanup():
    assert normalize_candidate_name('  Ridge   Alpha  ') == 'Ridge Alpha'

@pytest.mark.parametrize('bad',['',' ', '=1+1','+SUM(1)','@hack','a'*65])
def test_bad_names(bad):
    with pytest.raises(ValueError):normalize_candidate_name(bad)

def test_rename_preserves_identity_and_metrics():
    records=[dict(region='Site01',name='A',row=2,col=3,slope_deg=8),dict(region='Site04',name='B',row=2,col=3,slope_deg=9)]
    rename_candidate(records,0,'Primary Ridge')
    assert records[0]['name']=='Primary Ridge'
    assert (records[0]['region'],records[0]['row'],records[0]['col'],records[0]['slope_deg'])==('Site01',2,3,8)

def test_duplicate_name_same_region_rejected():
    rec=[dict(region='Site01',name='A'),dict(region='Site01',name='B')]
    with pytest.raises(ValueError):rename_candidate(rec,1,'a')

def test_same_name_different_region_ok():
    rec=[dict(region='Site01',name='A'),dict(region='Site04',name='B')]
    rename_candidate(rec,1,'A')
    assert rec[1]['name']=='A'

def test_csv_preserves_user_names(tmp_path):
    rows=[dict(region='Site01',name='Ridge Alpha',row=1,col=2,x_projected_m=0,y_projected_m=1,elevation_m=2,slope_deg=3,elevation_rms_m=4,slope_rms_deg=5,lola_spot_count=0)]
    output=export_candidates(tmp_path/'out.csv',rows)
    assert 'Ridge Alpha' in output.read_text()
    assert 'Site01' in output.read_text()

def test_discover_only_local_files(tmp_path):
    assert discover(tmp_path)==[]
    paths=region_paths(tmp_path,'Site04')
    for k in ('Elevation','Slope'):paths[k].parent.mkdir(parents=True,exist_ok=True);paths[k].touch()
    found=discover(tmp_path)
    assert found[0]['id']=='Site04' and found[0]['complete'] is False
