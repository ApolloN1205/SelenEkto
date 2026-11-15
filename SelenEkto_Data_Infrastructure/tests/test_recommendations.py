import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import pytest
from selenekto_v2.recommendations import evaluate, DEFAULT_WEIGHTS
A = {'name':'A','region':'Site01','slope_deg':5,'elevation_rms_m':.2,'slope_rms_deg':1,'lola_spot_count':3}
B = {'name':'B','region':'Site04','slope_deg':12,'elevation_rms_m':.4,'slope_rms_deg':2,'lola_spot_count':0}
def test_better_metrics_score_higher():
    result=evaluate([A,B],DEFAULT_WEIGHTS)['rows']
    assert result[0]['name']=='A' and result[0]['score']>result[1]['score']
def test_missing_data_not_scored():
    rows=evaluate([A,{**B,'slope_deg':None}],DEFAULT_WEIGHTS)['rows']
    assert rows[-1]['score'] is None
    assert 'Gentler slope (slope_deg)' in rows[-1]['missing']
def test_ignored_missing_metric_allowed():
    weights={key:0 for key in DEFAULT_WEIGHTS};weights['Gentler slope']=5
    rows=evaluate([A,{**B,'elevation_rms_m':None}],weights)['rows']
    assert all(row['score'] is not None for row in rows)
def test_ties_stay_tied():
    rows=evaluate([A,dict(A,name='A2')],DEFAULT_WEIGHTS)['rows']
    assert rows[0]['score']==rows[1]['score']==50.0
def test_all_zero_weights_rejected():
    with pytest.raises(ValueError): evaluate([A,B],{key:0 for key in DEFAULT_WEIGHTS})
def test_one_candidate_rejected():
    with pytest.raises(ValueError):evaluate([A],DEFAULT_WEIGHTS)
