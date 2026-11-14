import csv
import pytest
from selenekto_data.candidate_horizons import parse_candidates, summarize_profile


def test_map_csv(tmp_path):
    p=tmp_path/'c.csv'
    with p.open('w',newline='') as fh:
        w=csv.DictWriter(fh,fieldnames=['name','row','col','slope_deg'])
        w.writeheader();w.writerow({'name':'A','row':4,'col':5,'slope_deg':10})
    assert parse_candidates(p,20,20)==[{'name':'A','row':4,'col':5}]


def test_rejects_duplicate_cells(tmp_path):
    p=tmp_path/'c.csv'
    p.write_text('name,row,col\nA,1,2\nB,1,2\n')
    with pytest.raises(ValueError,match='Duplicate'):
        parse_candidates(p,10,10)


def test_rejects_outside_grid(tmp_path):
    p=tmp_path/'c.csv'
    p.write_text('name,row,col\nA,10,2\n')
    with pytest.raises(ValueError,match='outside'):
        parse_candidates(p,10,10)


def test_summarize_profile():
    records=[{'horizon_angle_deg':2,'controlling_distance_m':10,'controlling_measurement_count':0,'boundary_truncated':False,'missing_elevation_samples':0},
             {'horizon_angle_deg':4,'controlling_distance_m':40,'controlling_measurement_count':1,'boundary_truncated':True,'missing_elevation_samples':1}]
    r=summarize_profile(records)
    assert r['mean_horizon_deg']==3 and r['furthest_controlling_cell_m']==40
    assert r['zero_lola_controlling_directions']==1 and r['edge_truncated_directions']==1
