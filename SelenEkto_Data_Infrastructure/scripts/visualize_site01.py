"""Create a four-panel visualization from the four Site01 LOLA GeoTIFFs.

This script only reads the original NASA files. It writes PNG and JSON outputs
under data/processed/visualizations and never modifies the source rasters.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data" / "raw" / "lola" / "Site01"
OUTPUT = ROOT / "data" / "processed" / "visualizations"

LAYERS = {
    "Elevation": {
        "file": "Site01_final_adj_5mpp_surf.tif",
        "unit": "Elevation (m)",
    },
    "Measurement count": {
        "file": "Site01_final_adj_5mpp_ldec.tif",
        "unit": "LOLA measurements per pixel",
    },
    "Elevation uncertainty": {
        "file": "Site01_final_adj_5mpp_toterr.tif",
        "unit": "RMS elevation uncertainty (m)",
    },
    "Slope": {
        "file": "Site01_final_adj_5mpp_slp.tif",
        "unit": "Slope (degrees)",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    arrays: dict[str, np.ma.MaskedArray] = {}
    statistics: dict[str, dict[str, object]] = {}
    reference = None

    for name, info in LAYERS.items():
        path = BASE / info["file"]
        if not path.is_file():
            raise FileNotFoundError(
                f"Required NASA file not found: {path}\n"
                "Check that all four Site01 GeoTIFFs are in data/raw/lola/Site01."
            )

        with rasterio.open(path) as dataset:
            current = {
                "width": dataset.width,
                "height": dataset.height,
                "crs": dataset.crs,
                "transform": dataset.transform,
                "bounds": dataset.bounds,
            }
            if reference is None:
                reference = current
            else:
                for key in ("width", "height", "crs", "transform", "bounds"):
                    if current[key] != reference[key]:
                        raise ValueError(f"Raster grid mismatch for {name}: {key} differs")

            masked = np.ma.masked_invalid(dataset.read(1, masked=True))
            values = masked.compressed()
            values = values[np.isfinite(values)]
            if values.size == 0:
                raise ValueError(f"No valid pixels found in {name}: {path}")

            arrays[name] = masked
            statistics[name] = {
                "source_file": info["file"],
                "unit_from_product_documentation": info["unit"],
                "valid_pixels": int(values.size),
                "total_pixels": int(dataset.width * dataset.height),
                "minimum": float(values.min()),
                "maximum": float(values.max()),
                "mean": float(values.mean()),
                "median": float(np.median(values)),
                "standard_deviation": float(values.std()),
                "percentile_2": float(np.percentile(values, 2)),
                "percentile_98": float(np.percentile(values, 98)),
                "sha256": sha256_file(path),
            }
            print(f"{name}: {values.size:,} valid pixels")

    assert reference is not None
    bounds = reference["bounds"]
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]
    fig, axes = plt.subplots(2, 2, figsize=(16, 13), constrained_layout=True)

    for ax, (name, info) in zip(axes.flat, LAYERS.items()):
        stats = statistics[name]
        image = ax.imshow(
            arrays[name],
            cmap="gray",
            origin="upper",
            extent=extent,
            vmin=stats["percentile_2"],
            vmax=stats["percentile_98"],
            interpolation="nearest",
        )
        ax.set_title(name, fontsize=14)
        ax.set_xlabel("Polar stereographic X (m)")
        ax.set_ylabel("Polar stereographic Y (m)")
        ax.set_aspect("equal")
        fig.colorbar(image, ax=ax, shrink=0.82, label=info["unit"])

    fig.suptitle("SELENEKTO | SITE01 | NASA LOLA DATA", fontsize=18, fontweight="bold")
    fig.text(
        0.5,
        0.01,
        "Each panel uses its own 2nd–98th percentile display stretch; "
        "original NASA rasters are unchanged.",
        ha="center",
        fontsize=9,
    )

    image_path = OUTPUT / "Site01_data_layers.png"
    stats_path = OUTPUT / "Site01_statistics.json"
    fig.savefig(image_path, dpi=180, facecolor="white")
    plt.close(fig)

    report = {
        "site": "Site01",
        "source": "NASA/GSFC PGDA LOLA 5 m/pixel landing-site products",
        "grid": {
            "width": reference["width"],
            "height": reference["height"],
            "bounds_projected_metres": [
                bounds.left, bounds.bottom, bounds.right, bounds.top
            ],
            "resolution_metres": [5.0, 5.0],
            "crs_wkt": reference["crs"].to_wkt() if reference["crs"] else None,
        },
        "layers": statistics,
        "note": "Display statistics are descriptive; verify product metadata and units before scientific interpretation.",
    }
    stats_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print("\n===== SELENEKTO VISUALISATION COMPLETE =====")
    print(f"Image: {image_path}")
    print(f"Statistics: {stats_path}")
    print("All four raster grids passed alignment checks.")


if __name__ == "__main__":
    main()
