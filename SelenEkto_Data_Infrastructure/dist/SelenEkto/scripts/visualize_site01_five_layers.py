"""Create a five-layer QA visualisation and statistics report for PGDA Site01.

Run from the SelenEkto_Data_Infrastructure directory:
    .venv\\Scripts\\python.exe scripts\\visualize_site01_five_layers.py

Reads original NASA GeoTIFFs without modifying them. Outputs:
    data/processed/visualizations/Site01_five_layers.png
    data/processed/visualizations/Site01_five_layer_statistics.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rasterio

BASE = Path("data/raw/lola/Site01")
OUTPUT = Path("data/processed/visualizations")

LAYERS = [
    {
        "key": "elevation",
        "title": "Elevation",
        "file": "Site01_final_adj_5mpp_surf.tif",
        "unit": "Surface elevation (m)",
        "description": "Surface-interpolated LOLA elevation; values are metres.",
    },
    {
        "key": "measurement_count",
        "title": "LOLA measurement count",
        "file": "Site01_final_adj_5mpp_ldec.tif",
        "unit": "LOLA spots per pixel",
        "description": "Number of LOLA spots recorded in each raster pixel.",
    },
    {
        "key": "elevation_uncertainty",
        "title": "Elevation uncertainty",
        "file": "Site01_final_adj_5mpp_toterr.tif",
        "unit": "RMS elevation error (m)",
        "description": "Total Z uncertainty, documented as RMS error in metres.",
    },
    {
        "key": "slope",
        "title": "Slope",
        "file": "Site01_final_adj_5mpp_slp.tif",
        "unit": "Slope (degrees)",
        "description": "Terrain slope in degrees.",
    },
    {
        "key": "slope_uncertainty",
        "title": "Slope uncertainty",
        "file": "Site01_final_adj_5mpp_slperr.tif",
        "unit": "RMS slope error (degrees)",
        "description": "Slope uncertainty, documented as RMS error in degrees.",
    },
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ma.MaskedArray] = {}
    report: dict[str, object] = {
        "site_id": "Site01",
        "site_name": "Connecting Ridge",
        "source": "NASA/GSFC Planetary Geodynamics Data Archive (PGDA), LOLA 5 m/pixel landing-site products",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "interpretation_note": (
            "Descriptive raster statistics only. They do not by themselves establish "
            "landing suitability, measurement independence, or scientific accuracy. "
            "LDEC counts spots per pixel; a valid interpolated LDEM value does not "
            "necessarily imply a direct LOLA spot in that pixel."
        ),
        "layers": {},
    }

    reference = None
    for layer in LAYERS:
        path = BASE / layer["file"]
        if not path.is_file():
            print(f"ERROR: Required layer is missing: {path}", file=sys.stderr)
            return 2

        with rasterio.open(path) as ds:
            grid = {
                "width": ds.width,
                "height": ds.height,
                "crs": ds.crs.to_wkt() if ds.crs else None,
                "transform": tuple(ds.transform),
                "bounds": tuple(ds.bounds),
                "resolution": tuple(ds.res),
            }
            if reference is None:
                reference = grid
            else:
                checks = {
                    "width": grid["width"] == reference["width"],
                    "height": grid["height"] == reference["height"],
                    "crs": grid["crs"] == reference["crs"],
                    "transform": grid["transform"] == reference["transform"],
                    "bounds": grid["bounds"] == reference["bounds"],
                }
                failed = [name for name, passed in checks.items() if not passed]
                if failed:
                    print(
                        f"ERROR: {layer['title']} grid does not match the first layer: "
                        + ", ".join(failed),
                        file=sys.stderr,
                    )
                    return 3

            data = ds.read(1, masked=True)
            data = np.ma.masked_invalid(data)
            values = np.asarray(data.compressed(), dtype=np.float64)
            values = values[np.isfinite(values)]
            if values.size == 0:
                print(f"ERROR: No valid values in {path}", file=sys.stderr)
                return 4

            arrays[layer["key"]] = data
            layer_report = {
                "title": layer["title"],
                "source_file": layer["file"],
                "documented_unit": layer["unit"],
                "description": layer["description"],
                "width": ds.width,
                "height": ds.height,
                "resolution_xy_metres": list(ds.res),
                "valid_pixels": int(values.size),
                "total_pixels": int(ds.width * ds.height),
                "missing_or_masked_pixels": int(ds.width * ds.height - values.size),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
                "mean": float(np.mean(values)),
                "median": float(np.median(values)),
                "standard_deviation": float(np.std(values)),
                "percentile_2": float(np.percentile(values, 2)),
                "percentile_98": float(np.percentile(values, 98)),
                "file_size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            if layer["key"] == "measurement_count":
                unique, counts = np.unique(values, return_counts=True)
                layer_report["spot_count_distribution"] = {
                    str(int(value)) if float(value).is_integer() else str(float(value)): int(count)
                    for value, count in zip(unique, counts)
                }
                layer_report["pixels_with_at_least_one_spot"] = int(np.count_nonzero(values > 0))
                layer_report["percentage_with_at_least_one_spot"] = float(np.count_nonzero(values > 0) / values.size * 100)
            report["layers"][layer["key"]] = layer_report
            print(f"OK  {layer['title']}: {values.size:,}/{ds.width * ds.height:,} valid pixels")

    assert reference is not None
    report["grid"] = {
        "width": reference["width"],
        "height": reference["height"],
        "bounds_projected_metres": list(reference["bounds"]),
        "resolution_xy_metres": list(reference["resolution"]),
        "crs_wkt": reference["crs"],
        "all_five_layers_aligned": True,
    }

    # Display each layer with its own robust stretch. The maps are for visual
    # inspection; their grayscale brightness is not directly comparable.
    fig, axes = plt.subplots(2, 3, figsize=(19, 12), constrained_layout=True)
    axes_flat = axes.ravel()
    bounds = reference["bounds"]
    extent = [bounds[0], bounds[2], bounds[1], bounds[3]]

    for index, layer in enumerate(LAYERS):
        ax = axes_flat[index]
        data = arrays[layer["key"]]
        layer_stats = report["layers"][layer["key"]]
        image = ax.imshow(
            data,
            cmap="gray",
            origin="upper",
            extent=extent,
            vmin=layer_stats["percentile_2"],
            vmax=layer_stats["percentile_98"],
            interpolation="nearest",
        )
        ax.set_title(layer["title"], fontsize=13, pad=10)
        ax.set_xlabel("Polar stereographic X (m)")
        ax.set_ylabel("Polar stereographic Y (m)")
        ax.set_aspect("equal")
        fig.colorbar(image, ax=ax, shrink=0.78, label=layer["unit"])

    axes_flat[5].axis("off")
    axes_flat[5].text(
        0.02, 0.95,
        "SELENEKTO | SITE01\nNASA LOLA five-layer inspection\n\n"
        "All five raster grids passed alignment checks.\n"
        "Each panel uses its own 2nd–98th percentile display stretch.\n"
        "Brightness must not be compared across different panels.\n\n"
        "Source measurements and original files are unchanged.",
        va="top", ha="left", fontsize=12, transform=axes_flat[5].transAxes,
    )
    fig.suptitle("SELENEKTO — CONNECTING RIDGE (SITE01)", fontsize=18, fontweight="bold")

    image_path = OUTPUT / "Site01_five_layers.png"
    report_path = OUTPUT / "Site01_five_layer_statistics.json"
    fig.savefig(image_path, dpi=170, facecolor="white")
    plt.close(fig)
    report["outputs"] = {
        "visualisation": str(image_path),
        "statistics_report": str(report_path),
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n===== SELENEKTO FIVE-LAYER ANALYSIS COMPLETE =====")
    print(f"Image: {image_path}")
    print(f"Statistics: {report_path}")
    print("All five raster grids have matching dimensions, CRS, transform and bounds.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
