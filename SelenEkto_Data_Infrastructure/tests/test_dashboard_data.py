import json
from pathlib import Path
import pytest
from selenekto_data.dashboard_data import discover_regions,read_candidate_comparison,latest_candidate_report,normalized_weight_label,candidate_label


def test_discovery_requires_both_rasters(tmp_path):
    root=tmp_path/'lola';r=root/'Site01';r.mkdir(parents=True)
    (r/'Site01_final_adj_5mpp_surf.tif').touch()
    assert discover_regions(root)==[]
    (r/'Site01_final_adj_5mpp_slp.tif').touch()
    assert discover_regions(root)==['Site01']


def test_missing_region_root(tmp_path):
    assert discover_regions(tmp_path/'absent')==[]


def test_report_reads_existing_only(tmp_path):
    assert read_candidate_comparison(tmp_path/'missing.json')==[]
    report=tmp_path/'2026-11-14'/'candidate_solar_comparison.json';report.parent.mkdir()
    report.write_text(json.dumps({'comparison':[{'name':'A','weighted_score':0.7}]}))
    assert latest_candidate_report(tmp_path)==report
    assert read_candidate_comparison(report)[0]['name']=='A'


def test_invalid_report_rejected(tmp_path):
    p=tmp_path/'bad.json';p.write_text('{"comparison": {}}')
    with pytest.raises(ValueError):read_candidate_comparison(p)


def test_weights_and_labels():
    assert normalized_weight_label('2','1','0')==(2.0,1.0,0.0)
    for case in [('0','0','0'),('-1','2','1'),('11','1','1')]:
        with pytest.raises(ValueError):normalized_weight_label(*case)
    assert 'Candidate 01' in candidate_label({'name':'Candidate 01','row':3,'col':4})
