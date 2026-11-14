from pathlib import Path
import pytest
from selenekto_data.repair_utils import pgda_url, comparable_candidates, valid_value, candidate_display, save_path


def test_nested_nasa_url():
    assert pgda_url('Site04', 'Site04_final_adj_5mpp_surf.tif') == 'https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif'


def test_nested_nasa_url_non_site_region():
    assert '/LM8/LM8_final_adj_5mpp_slp.tif' in pgda_url('LM8', 'LM8_final_adj_5mpp_slp.tif')


def test_nasa_url_rejects_unexpected_path():
    with pytest.raises(ValueError): pgda_url('Site04', '../Site01_final_adj_5mpp_surf.tif')


def test_select_exact_candidate_indices():
    items = [{'name': 'A'}, {'name': 'B'}, {'name': 'C'}]
    assert comparable_candidates(items, [0, 2]) == [items[0], items[2]]


def test_select_requires_two():
    with pytest.raises(ValueError): comparable_candidates([{'name':'a'}], [0])


def test_select_rejects_repeated_index():
    with pytest.raises(ValueError): comparable_candidates([1, 2], [0, 0])


def test_missing_values_not_cast_to_zero():
    assert valid_value('') is None
    assert valid_value(None) is None
    assert valid_value('nan') is None
    assert valid_value('2.5') == 2.5


def test_candidate_labels_and_path():
    assert 'Site01' in candidate_display({'region':'Site01','name':'Alpha','row':1,'col':2})
    assert save_path(Path('/tmp/project')).name == 'saved_named_candidates.csv'
