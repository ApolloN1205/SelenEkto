from selenekto_v2.settings_store import DEFAULTS, normalize, load_settings, save_settings, theme_stylesheet

def test_default_missing(tmp_path):
    assert load_settings(tmp_path) == DEFAULTS

def test_roundtrip(tmp_path):
    data = dict(DEFAULTS, accent='Ice blue', solar_duration_hours=168, default_layer='Slope')
    path=save_settings(tmp_path,data)
    assert path.exists()
    assert load_settings(tmp_path) == data

def test_invalid_values_rejected():
    found=normalize({'theme':'surprise','font_size':-50,'solar_duration_hours':True,'confirm_candidate_removal':'no','accent':'Coral'})
    assert found['theme']=='Obsidian'
    assert found['font_size']==12
    assert found['solar_duration_hours']==72
    assert found['confirm_candidate_removal'] is True
    assert found['accent']=='Coral'

def test_bad_json_falls_back(tmp_path):
    path=tmp_path/'data/config/desktop_settings.json';path.parent.mkdir(parents=True)
    path.write_text('{bad',encoding='utf-8')
    assert load_settings(tmp_path)==DEFAULTS

def test_theme_changes(tmp_path):
    style=theme_stylesheet('QWidget {background:#080A0D;}',{'theme':'Graphite','accent':'Ice blue','font_size':15})
    assert '#1A1D23' in style
    assert '#5EC8F8' in style
    assert '15px' in style


def test_new_accent_values_and_persistence(tmp_path):
    from selenekto_v2.settings_store import ACCENTS
    assert ACCENTS['Aurora LOLA'] == '#C4A1FF'
    assert ACCENTS['Crimson'] == '#E54864'
    for name in ('Aurora LOLA', 'Crimson'):
        save_settings(tmp_path, dict(DEFAULTS, accent=name))
        assert load_settings(tmp_path)['accent'] == name
        assert ACCENTS[name] in theme_stylesheet('QWidget {}', {'accent':name})
