from pathlib import Path
import json
import hashlib

from selenekto_data.validation import validate_registry

ROOT = Path(__file__).resolve().parents[1]


def test_registry_has_no_structural_issues_when_no_files_are_downloaded():
    assert validate_registry(ROOT) == []


def test_checksum_validation_detects_modified_file(tmp_path):
    # Use a copied, isolated mini repository so the real project fixture is not changed.
    (tmp_path / "data/catalog").mkdir(parents=True)
    (tmp_path / "data/manifests").mkdir(parents=True)
    (tmp_path / "data/raw/lola/Site01").mkdir(parents=True)
    catalog = json.loads((ROOT / "data/catalog/landing_sites.json").read_text())
    (tmp_path / "data/catalog/landing_sites.json").write_text(json.dumps(catalog))
    sample = tmp_path / "data/raw/lola/Site01/sample.tif"
    sample.write_bytes(b"synthetic fixture, not a real raster")
    digest = hashlib.sha256(sample.read_bytes()).hexdigest()
    registry = {"schema_version":"1.0","datasets":[{
        "dataset_id":"SAMPLE", "download_url":"https://pgda.gsfc.nasa.gov/sample.tif",
        "local_path":"data/raw/lola/Site01/sample.tif", "acquisition_status":"downloaded",
        "sha256":digest, "file_size_bytes":sample.stat().st_size
    }]}
    (tmp_path / "data/manifests/datasets.json").write_text(json.dumps(registry))
    assert validate_registry(tmp_path) == []
    sample.write_bytes(b"changed")
    assert any("checksum mismatch" in issue for issue in validate_registry(tmp_path))
