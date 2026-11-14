from affine import Affine
from selenekto_data.site_map import xy_to_cell, centre_xy, terrain_record

def test_reference_centre():
    transform = Affine(5,0,-19000,0,-5,-4000)
    x,y=centre_xy(transform,1599,1600)
    assert (x,y)==(-10997.5,-11997.5)
    assert xy_to_cell(transform,x,y,3200,3200)==(1599,1600)

def test_bounds_and_bad_inputs():
    t=Affine(5,0,-19000,0,-5,-4000)
    assert xy_to_cell(t,-20000,-10000,3200,3200) is None
    assert xy_to_cell(t,float('nan'),-12000,3200,3200) is None
    assert xy_to_cell(t,-18999,-4001,3200,3200)==(0,0)

def test_record_preserves_missing_layer():
    t=Affine(5,0,-19000,0,-5,-4000)
    d=terrain_record(1,2,{'elevation_m':123.0,'slope_deg':2.5,'lola_spot_count':0},t)
    assert d['elevation_m']==123.0
    assert d['elevation_rms_m'] is None
    assert d['lola_spot_count']==0
