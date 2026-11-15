import json
from pathlib import Path
from selenekto_v2.region_data import enrich_profile, load_profiles, metric_value, prepare_profiles


def sample_profile():
    layers={}
    for key in ('elevation','slope','elevation_uncertainty','slope_uncertainty','measurement_count'):
        layers[key]={'status':'ready','statistics':{
            'minimum':0,'maximum':12,'mean':2.5,'median':2.0,'valid_pixels':100,
            'valid_coverage_percent':100,'standard_deviation_population':1.0,
            'quantile_method':'overview sample'}}
    layers['measurement_count']['statistics']['pixels_with_at_least_one_spot_percent']=9.3
    return {'site_code':'Site01','region_name':'Connecting Ridge','availability':'ready','layers':layers}


def test_enrich_has_all_five_fields_without_replacing_stats():
    original=sample_profile()
    d=enrich_profile(original)
    assert len(d['readable_metrics']) == 5
    assert d['layers'] == original['layers']
    assert d['readable_metrics']['slope']['mean']==2.5
    assert metric_value(d,'Direct LOLA coverage (%)')==9.3


def test_missing_not_zero():
    d=sample_profile()
    d['layers']['slope']={'status':'missing_file','statistics':None}
    enriched=enrich_profile(d)
    assert metric_value(enriched,'Mean slope (°)') is None
    assert enriched['readable_metrics']['slope']['status']=='missing_file'


def test_prepare_preserves_existing_metadata(tmp_path):
    f=tmp_path/'Site01_terrain_profile.json'
    d=sample_profile();d['dataset_provenance']=[{'file':'real.tif'}]
    f.write_text(json.dumps(d),encoding='utf-8')
    results=prepare_profiles(tmp_path)
    assert len(results)==1
    result=json.loads(f.read_text(encoding='utf-8'))
    assert result['dataset_provenance']==d['dataset_provenance']
    assert result['readable_metrics']['elevation']['mean']==2.5
    assert len(load_profiles(tmp_path))==1


def test_repeated_enrichment_idempotent(tmp_path):
    f=tmp_path/'Site01_terrain_profile.json'
    f.write_text(json.dumps(sample_profile()),encoding='utf-8')
    prepare_profiles(tmp_path)
    once=json.loads(f.read_text(encoding='utf-8'))
    prepare_profiles(tmp_path)
    assert json.loads(f.read_text(encoding='utf-8'))==once


def test_invalid_profile_is_reported_not_invented(tmp_path):
    (tmp_path/'Site04_terrain_profile.json').write_text('broken',encoding='utf-8')
    r=prepare_profiles(tmp_path)
    assert r[0]['status']=='profile_error'
    assert load_profiles(tmp_path)[0]['availability']=='invalid_profile'
