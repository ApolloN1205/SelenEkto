from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

rasterio = pytest.importorskip("rasterio")
from rasterio.transform import from_origin

from selenekto_data.terrain import analyze_site


PRODUCTS = {
    "surface_elevation": ("LDEM", "elevation.tif", "m"),
    "measurement_count": ("LDEC", "count.tif", "count"),
    "elevation_uncertainty": ("TOTAL_Z_UNCERTAINTY", "zerr.tif", "m"),
    "slope": ("SLOPE", "slope.tif", "degree"),
    "slope_uncertainty": ("SLOPE_UNCERTAINTY", "slperr.tif", "degree"),
}


def _make_root(tmp_path: Path) -> Path:
    root = tmp_path
    raster_dir = root / "data/raw/lola/Site01"
    raster_dir.mkdir(parents=True)
    transform = from_origin(100.0, 200.0, 5.0, 5.0)
    crs = "EPSG:3857"
    values = {
        "surface_elevation": np.array([[10, 11], [12, 13]], dtype="float32"),
        "measurement_count": np.array([[0, 1], [2, 1]], dtype="float32"),
        "elevation_uncertainty": np.array([[0.2, 0.3], [0.4, 0.5]], dtype="float32"),
        "slope": np.array([[1, 2], [3, 4]], dtype="float32"),
        "slope_uncertainty": np.array([[0.1, 0.2], [0.3, 0.4]], dtype="float32"),
    }
    records = []
    for product_type, (suffix, filename, _unit) in PRODUCTS.items():
        path = raster_dir / filename
        with rasterio.open(
            path, "w", driver="GTiff", width=2, height=2, count=1,
            dtype="float32", crs=crs, transform=transform, nodata=-9999.0,
        ) as dst:
            dst.write(values[product_type], 1)
        import hashlib
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        records.append({
            "dataset_id": f"PGDA_SITE01_{suffix}",
            "site_code": "Site01",
            "region_name": "Connecting Ridge",
            "product_type": product_type,
            "product_name": product_type,
            "download_url": "https://pgda.gsfc.nasa.gov/example.tif",
            "local_path": str(path.relative_to(root)).replace("\\", "/"),
            "file_size_bytes": path.stat().st_size,
            "sha256": digest,
        })

    (root / "data/manifests").mkdir(parents=True)
    (root / "data/manifests/datasets.json").write_text(
        json.dumps({"datasets": records}), encoding="utf-8"
    )
    (root / "data/catalog").mkdir(parents=True)
    (root / "data/catalog/landing_sites.json").write_text(json.dumps({
        "sites": [{
            "id": "CONNECTING_RIDGE", "name": "Connecting Ridge", "short_name": "R01",
            "latitude_deg": -89.4632, "longitude_as_published_deg": -137.49,
            "longitude_convention": "published; conversion not applied",
            "coordinate_frame": "MOON_ME", "coordinate_role": "representative_region_centre",
            "coordinate_source": {"url": "https://ntrs.nasa.gov/citations/20250002845"},
            "coordinate_quality_note": "Representative region centre only.",
        }]
    }), encoding="utf-8")
    return root


def test_analyze_site_writes_profile_and_counts_ladec(tmp_path):
    root = _make_root(tmp_path)
    report = analyze_site("Site01", root=root, output_dir="data/processed/site_profiles")
    assert report["region_name"] == "Connecting Ridge"
    assert report["grid"]["all_five_layers_match"] is True
    assert report["layers"]["measurement_count"]["statistics"]["pixels_with_at_least_one_spot"] == 3
    assert report["layers"]["elevation"]["statistics"]["mean"] == pytest.approx(11.5)
    output = root / "data/processed/site_profiles/Site01_terrain_profile.json"
    assert output.is_file()
    json.loads(output.read_text(encoding="utf-8"))


def test_analyze_site_rejects_grid_mismatch(tmp_path):
    root = _make_root(tmp_path)
    path = root / "data/raw/lola/Site01/slperr.tif"
    with rasterio.open(path, "w", driver="GTiff", width=2, height=2, count=1,
                       dtype="float32", crs="EPSG:3857", transform=from_origin(101, 200, 5, 5)) as dst:
        dst.write(np.ones((2, 2), dtype="float32"), 1)
    import hashlib
    records_path = root / "data/manifests/datasets.json"
    payload = json.loads(records_path.read_text(encoding="utf-8"))
    item = next(x for x in payload["datasets"] if x["product_type"] == "slope_uncertainty")
    item["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    item["file_size_bytes"] = path.stat().st_size
    records_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="Raster grid mismatch"):
        analyze_site("Site01", root=root)


def test_analyze_site_rejects_checksum_mismatch(tmp_path):
    root = _make_root(tmp_path)
    records_path = root / "data/manifests/datasets.json"
    payload = json.loads(records_path.read_text(encoding="utf-8"))
    payload["datasets"][0]["sha256"] = "0" * 64
    records_path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        analyze_site("Site01", root=root)
