import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE=Path(__file__).resolve().parents[1]/'src/selenekto_v2/offline_library.py'
spec=importlib.util.spec_from_file_location('offline_library',MODULE)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class TestLibrary(unittest.TestCase):
    def test_all_27_unique(self):
        self.assertEqual(len(mod.REGIONS),27)
        self.assertEqual(len(set(mod.REGIONS)),27)
    def test_no_fake_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            x=mod.catalogue_status(tmp,'Site01')
            self.assertEqual(x['present_layers'],0)
            self.assertFalse(x['preview'])
            self.assertEqual(mod.safe_profile(tmp,'Site01'),{})
    def test_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):mod.raster_path(tmp,'../../elsewhere','slp')
            with self.assertRaises(ValueError):mod.raster_path(tmp,'Site01','bad')
    def test_known_warnings(self):
        self.assertIn('Site20',mod.KNOWN_ISSUES)
        self.assertIn('Site23',mod.KNOWN_ISSUES)
        self.assertIn('LM8',mod.KNOWN_ISSUES)
    def test_preview_naming(self):
        self.assertEqual(mod.preview_path('/any','Site04').name,'Site04_elevation.png')
if __name__=='__main__':unittest.main()
