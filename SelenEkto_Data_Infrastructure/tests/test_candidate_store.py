from selenekto_data.candidate_store import CandidateStore
import pytest

def cell(r, c):
    return {'row': r, 'col': c, 'elevation_m': 42.0}

def test_add_shows_and_retains_selected_data():
    s=CandidateStore(); a=s.add(cell(10, 20))
    assert a['name']=='Candidate 01'
    assert s.as_rows()[0]['row']==10
    assert len(s.as_rows())==1

def test_second_cell_and_duplicate_rejection():
    s=CandidateStore(); s.add(cell(10,20)); s.add(cell(11,20))
    assert len(s.as_rows())==2
    with pytest.raises(ValueError,match='already'):
        s.add(cell(10,20))

def test_remove_and_monotonic_names():
    s=CandidateStore(); s.add(cell(1,1)); s.add(cell(2,2));s.remove_positions([0])
    assert s.as_rows()[0]['name']=='Candidate 02'
    assert s.add(cell(3,3))['name']=='Candidate 03'

def test_missing_selection():
    with pytest.raises(ValueError, match='Click'):
        CandidateStore().add(None)
