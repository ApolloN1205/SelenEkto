import sys
from pathlib import Path
import json
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from fix_release_profile_privacy import safe_string,sanitize_stage

class PrivacyTests(unittest.TestCase):
    def test_absolute_windows_raster_path(self):
        self.assertEqual(safe_string(r'C:\Users\someone\OneDrive\Project\data\raw\lola\Site01\a_slp.tif'),
                         'data/raw/lola/Site01/a_slp.tif')
    def test_other_user_path_refused(self):
        with self.assertRaises(ValueError):safe_string(r'C:\Users\someone\Desktop\private_note.txt')
    def test_science_data_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)/'stage'; folder=stage/'data/catalog/region_profiles';folder.mkdir(parents=True)
            path=folder/'Site01_terrain_profile.json'
            path.write_text(json.dumps({'mean_slope_deg':12.5,'paths':[r'C:\Users\someone\Project\data\raw\lola\Site01\slope.tif']}))
            inventory=folder/'local_raster_inventory.json';inventory.write_text('{}')
            changed,removed=sanitize_stage(stage,Path(td)/'backup')
            self.assertEqual((changed,removed),(1,1))
            data=json.loads(path.read_text())
            self.assertEqual(data['mean_slope_deg'],12.5)
            self.assertEqual(data['paths'][0],'data/raw/lola/Site01/slope.tif')
            self.assertFalse(inventory.exists())
    def test_no_partial_change_on_unknown_private_path(self):
        with tempfile.TemporaryDirectory() as td:
            stage=Path(td)/'stage'; folder=stage/'data/catalog/region_profiles';folder.mkdir(parents=True)
            path=folder/'Site01_terrain_profile.json'
            raw=json.dumps({'path':r'C:\Users\someone\Desktop\secret.txt'})
            path.write_text(raw)
            with self.assertRaises(ValueError):sanitize_stage(stage,Path(td)/'backup')
            self.assertEqual(path.read_text(),raw)

if __name__=='__main__':unittest.main()
