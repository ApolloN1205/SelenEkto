"""Reusable, provenance-preserving analysis of co-registered PGDA LOLA rasters.

This module summarises the five Site01 raster layers. It does NOT calculate a
local topographic horizon, landing safety, illumination, or communications
availability. Those require additional reference-frame and geometric work.

Requires the optional ``geo`` extra (Rasterio) and NumPy.
"""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import numpy as np
    import rasterio
except ImportError as exc:  # pragma: no cover - exercised in installations without geo extra
    raise RuntimeError(
        "Terrain analysis requires NumPy and Rasterio. Install with: "
        "python -m pip install -e '.[geo]'"
    ) from exc

from .catalog import list_sites
from .paths import project_root
from .registry import list_datasets

# Registry product_type -> report key and provider-documented unit.
_REQUIRED_LAYERS: dict[str, tuple[str, str]] = {
    "surface_elevation": ("elevation", "m"),
    "measurement_count": ("measurement_count", "LOLA spots per pixel"),
    "elevation_uncertainty": ("elevation_uncertainty", "RMS error (m)"),
    "slope": ("slope", "degrees"),
    "slope_uncertainty": ("slope_uncertainty", "RMS error (degrees)"),
}


def _sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_local_path(root: Path, value: str) -> Path:
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe local_path in dataset registry: {value!r}")
    result = (root / relative).resolve()
    if root.resolve() not in result.parents:
        raise ValueError(f"Dataset path escapes project root: {value!r}")
    return result


def _numeric_summary(values: np.ndarray) -> dict[str, Any]:
    """Summarise finite, unmasked values using exact NumPy statistics."""
    finite = np.asarray(values)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        raise ValueError("Raster contains no finite, unmasked values")
    return {
        "valid_pixels": int(finite.size),
        "minimum": float(np.min(finite)),
        "maximum": float(np.max(finite)),
        "mean": float(np.mean(finite, dtype=np.float64)),
        "median": float(np.median(finite)),
        "standard_deviation_population": float(np.std(finite, dtype=np.float64)),
        "percentile_02": float(np.percentile(finite, 2)),
        "percentile_98": float(np.percentile(finite, 98)),
    }


def _catalogue_site_for_region(region_name: str, root: Path) -> dict[str, Any] | None:
    target = region_name.strip().casefold()
    for site in list_sites(root):
        if str(site.get("name", "")).strip().casefold() == target:
            return site
    return None


def _layer_records(site_code: str, root: Path) -> dict[str, dict[str, Any]]:
    records = [d for d in list_datasets(root) if str(d.get("site_code", "")).casefold() == site_code.casefold()]
    by_type: dict[str, dict[str, Any]] = {}
    for product_type, (report_key, _unit) in _REQUIRED_LAYERS.items():
        matches = [d for d in records if d.get("product_type") == product_type]
        if len(matches) != 1:
            raise ValueError(
                f"Expected exactly one {product_type!r} record for {site_code}; found {len(matches)}"
            )
        by_type[report_key] = matches[0]
    return by_type


def analyze_site(
    site_code: str,
    *,
    root: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Analyse the five registered LOLA layers for one PGDA site.

    Checks file presence, SHA-256 against the registry when available, single
    band, common raster dimensions/CRS/transform/bounds, and calculates
    descriptive statistics. Writes a JSON profile unless output_dir is None.

    The site coordinates are included as catalogue metadata only. This
    function deliberately does not transform them into raster X/Y coordinates
    or use them as an observer location.
    """
    base = Path(root).resolve() if root is not None else project_root()
    layers = _layer_records(site_code, base)

    first_grid: dict[str, Any] | None = None
    layer_results: dict[str, Any] = {}
    raw_region_names: set[str] = set()
    dataset_provenance: list[dict[str, Any]] = []

    for product_type, (report_key, documented_unit) in _REQUIRED_LAYERS.items():
        record = layers[report_key]
        region_name = str(record.get("region_name") or record.get("candidate_region_match") or "")
        if region_name:
            raw_region_names.add(region_name)

        local_path = record.get("local_path")
        if not local_path:
            raise ValueError(f"Registry record {record.get('dataset_id')} has no local_path")
        path = _safe_local_path(base, str(local_path))
        if not path.is_file():
            raise FileNotFoundError(
                f"Required layer {report_key!r} is missing: {path}. "
                f"Acquire it using the data CLI before analysing this site."
            )

        actual_size = path.stat().st_size
        actual_hash = _sha256(path)
        expected_hash = record.get("sha256")
        expected_size = record.get("file_size_bytes")
        if expected_hash and actual_hash.casefold() != str(expected_hash).casefold():
            raise ValueError(f"SHA-256 mismatch for {record.get('dataset_id')}: {path}")
        if expected_size is not None and int(expected_size) != actual_size:
            raise ValueError(f"File-size mismatch for {record.get('dataset_id')}: {path}")

        with rasterio.open(path) as ds:
            if ds.count != 1:
                raise ValueError(f"Expected one raster band for {report_key}; found {ds.count}")
            grid = {
                "width": int(ds.width),
                "height": int(ds.height),
                "crs_wkt": ds.crs.to_wkt() if ds.crs else None,
                "transform": [float(v) for v in tuple(ds.transform)[:6]],
                "bounds": [float(v) for v in tuple(ds.bounds)],
                "resolution_xy_m": [abs(float(ds.transform.a)), abs(float(ds.transform.e))],
                "nodata": float(ds.nodata) if ds.nodata is not None and math.isfinite(float(ds.nodata)) else None,
                "dtype": str(ds.dtypes[0]),
                "band_unit_in_file": ds.units[0] if ds.units else None,
            }
            if first_grid is None:
                first_grid = grid
            else:
                for field in ("width", "height", "crs_wkt", "transform", "bounds"):
                    if grid[field] != first_grid[field]:
                        raise ValueError(
                            f"Raster grid mismatch: {report_key}.{field} differs from the first layer"
                        )

            masked = ds.read(1, masked=True)
            masked = np.ma.masked_invalid(masked)
            values = masked.compressed()
            values = values[np.isfinite(values)]
            total_pixels = int(ds.width * ds.height)
            summary = _numeric_summary(values)

        summary.update({
            "total_pixels": total_pixels,
            "missing_or_masked_pixels": total_pixels - summary["valid_pixels"],
            "valid_coverage_percent": 100.0 * summary["valid_pixels"] / total_pixels,
        })

        if report_key == "measurement_count":
            rounded = np.rint(values)
            non_integer_count = int(np.count_nonzero(np.abs(values - rounded) > 1e-5))
            counts = Counter(int(v) for v in rounded if v >= 0 and abs(v - round(v)) <= 1e-5)
            summary["spot_count_distribution"] = [
                {
                    "spots_per_pixel": count,
                    "pixel_count": int(counts[count]),
                    "percentage_of_valid_pixels": 100.0 * counts[count] / summary["valid_pixels"],
                }
                for count in sorted(counts)
            ]
            summary["pixels_with_at_least_one_spot"] = int(np.count_nonzero(values > 0))
            summary["pixels_with_at_least_one_spot_percent"] = (
                100.0 * summary["pixels_with_at_least_one_spot"] / summary["valid_pixels"]
            )
            summary["non_integer_values"] = non_integer_count

        layer_results[report_key] = {
            "dataset_id": record.get("dataset_id"),
            "product_name": record.get("product_name"),
            "source_file": path.name,
            "source_url": record.get("download_url"),
            "unit_from_product_documentation": documented_unit,
            "statistics": summary,
        }
        dataset_provenance.append({
            "dataset_id": record.get("dataset_id"),
            "path": str(path.relative_to(base)),
            "file_size_bytes": actual_size,
            "sha256": actual_hash,
            "registry_sha256_matched": bool(expected_hash and actual_hash.casefold() == str(expected_hash).casefold()),
        })

    region_names = sorted(raw_region_names)
    region_name = region_names[0] if len(region_names) == 1 else (", ".join(region_names) or None)
    catalogue_site = _catalogue_site_for_region(region_name, base) if region_name else None

    report: dict[str, Any] = {
        "schema_version": "1.0",
        "report_type": "selenekto_site_terrain_profile",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site_code": site_code,
        "region_name": region_name,
        "catalogue_reference_point": None,
        "source": "NASA/GSFC Planetary Geodynamics Data Archive — LRO/LOLA 5 m/pixel landing-site products",
        "grid": {
            **(first_grid or {}),
            "pixel_count": int((first_grid or {}).get("width", 0) * (first_grid or {}).get("height", 0)),
            "projected_pixel_area_m2": abs(
                float((first_grid or {}).get("transform", [0, 0, 0, 0, 0, 0])[0])
                * float((first_grid or {}).get("transform", [0, 0, 0, 0, 0, 0])[4])
                - float((first_grid or {}).get("transform", [0, 0, 0, 0, 0, 0])[1])
                * float((first_grid or {}).get("transform", [0, 0, 0, 0, 0, 0])[3])
            ),
            "note": "Projected raster-grid metadata; do not interpret projected area as a geodesic lunar surface area without projection-scale treatment.",
            "all_five_layers_match": True,
        },
        "layers": layer_results,
        "dataset_provenance": dataset_provenance,
        "scientific_interpretation_limits": [
            "Descriptive statistics summarise the entire raster footprint, not a selected landing ellipse or a particular point.",
            "A valid interpolated LDEM pixel does not imply a direct LOLA laser spot exists in that same pixel.",
            "LDEC is measurement support information; do not treat a zero count as a missing elevation if the LDEM value is valid.",
            "RMS uncertainty is not a guarantee that every individual pixel error lies within that value.",
            "This report does not calculate a local topographic horizon, solar illumination, Earth visibility, landing safety, or actual power/communications performance.",
            "The catalogue reference coordinates are representative region centres, not precision landing targets. Coordinate transformation and longitude convention must be independently verified before use as an observer position.",
            "The raster WKT is a custom lunar south-polar stereographic definition. Confirm its full product documentation, registration and MOON_ME/DE421 relationship before combining with ephemerides.",
        ],
        "coordinate_reference": {
            "status": "catalogue_only_not_transformed",
            "note": "No latitude/longitude to raster X/Y transformation has been performed by this analysis.",
        },
    }

    if catalogue_site:
        report["catalogue_reference_point"] = {
            "id": catalogue_site.get("id"),
            "name": catalogue_site.get("name"),
            "short_name": catalogue_site.get("short_name"),
            "latitude_deg": catalogue_site.get("latitude_deg"),
            "longitude_as_published_deg": catalogue_site.get("longitude_as_published_deg"),
            "longitude_convention": catalogue_site.get("longitude_convention"),
            "coordinate_frame": catalogue_site.get("coordinate_frame"),
            "coordinate_role": catalogue_site.get("coordinate_role"),
            "source": catalogue_site.get("coordinate_source"),
            "note": catalogue_site.get("coordinate_quality_note"),
        }

    if output_dir is not None:
        out = Path(output_dir)
        if not out.is_absolute():
            out = base / out
        out.mkdir(parents=True, exist_ok=True)
        output_file = out / f"{site_code}_terrain_profile.json"
        temp_file = output_file.with_suffix(".json.tmp")
        temp_file.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temp_file.replace(output_file)
        report["output_file"] = str(output_file)

    return report
