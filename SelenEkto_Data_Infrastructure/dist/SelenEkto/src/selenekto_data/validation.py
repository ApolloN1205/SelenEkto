"""Validation of catalogue records, registered files and optional GeoTIFF metadata."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .catalog import validate_catalog
from .paths import project_root
from .registry import load_dataset_registry


def validate_registry(root: Path | None = None) -> list[str]:
    base = root or project_root()
    issues = validate_catalog(base)
    payload = load_dataset_registry(base)
    seen: set[str] = set()
    for index, item in enumerate(payload.get("datasets", [])):
        prefix = f"datasets[{index}]"
        dataset_id = item.get("dataset_id")
        if not dataset_id:
            issues.append(f"{prefix}: missing dataset_id")
        elif dataset_id in seen:
            issues.append(f"{prefix}: duplicate dataset_id {dataset_id}")
        seen.add(dataset_id)
        parsed = urlparse(item.get("download_url", ""))
        if parsed.scheme != "https" or parsed.hostname != "pgda.gsfc.nasa.gov":
            issues.append(f"{prefix}: download URL is not an HTTPS PGDA URL")
        if item.get("acquisition_status") == "downloaded":
            rel = Path(item.get("local_path", ""))
            if rel.is_absolute() or ".." in rel.parts:
                issues.append(f"{prefix}: unsafe local path")
                continue
            path = base / rel
            if not path.is_file():
                issues.append(f"{prefix}: marked downloaded but file is missing: {rel}")
                continue
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual = digest.hexdigest()
            if actual != item.get("sha256"):
                issues.append(f"{prefix}: checksum mismatch for {rel}")
            if item.get("file_size_bytes") != path.stat().st_size:
                issues.append(f"{prefix}: recorded file size mismatch for {rel}")
    return issues


def inspect_raster(path: str | Path) -> dict[str, Any]:
    """Return read-only raster metadata. Requires optional extra: pip install -e '.[geo]'."""
    try:
        import rasterio
    except ImportError as exc:
        raise RuntimeError("Raster inspection requires rasterio. Install with: pip install -e '.[geo]'") from exc
    raster_path = Path(path)
    with rasterio.open(raster_path) as dataset:
        transform = dataset.transform
        return {
            "path": str(raster_path), "driver": dataset.driver, "width": dataset.width,
            "height": dataset.height, "band_count": dataset.count, "dtypes": list(dataset.dtypes),
            "crs_wkt": dataset.crs.to_wkt() if dataset.crs else None,
            "crs_string": str(dataset.crs) if dataset.crs else None,
            "bounds": list(dataset.bounds), "transform": list(transform)[:6],
            "resolution_xy": [abs(transform.a), abs(transform.e)],
            "nodata": dataset.nodata, "units": list(dataset.units) if dataset.units else None,
            "block_shapes": [list(shape) for shape in dataset.block_shapes],
            "file_size_bytes": raster_path.stat().st_size,
            "warning": "Metadata inspection only. Confirm lunar projection parameters, registration, vertical reference and units against the product README before scientific use.",
        }
