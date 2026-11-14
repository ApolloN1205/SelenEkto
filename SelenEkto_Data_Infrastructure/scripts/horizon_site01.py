"""Generate Site01 terrain horizon report and graph from NASA PGDA rasters.
Run from SelenEkto_Data_Infrastructure root:
    python scripts/horizon_site01.py
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as convert_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from selenekto_data.horizon import MOON_RADIUS_M, calculate_horizon  # noqa: E402

# Representative region centre published in NASA Lunar Surface Data Book.
LAT, LON = -89.4632, -137.49
SOURCE_CRS = "+proj=longlat +R=1737400 +no_defs +type=crs"
DATA = ROOT / "data" / "raw" / "lola" / "Site01"
OUTPUT = ROOT / "data" / "processed" / "horizon" / "Site01"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-distance-m", type=float, default=5000)
    parser.add_argument("--sample-step-m", type=float, default=10)
    parser.add_argument("--azimuth-step-deg", type=float, default=1)
    parser.add_argument("--observer-height-m", type=float, default=0)
    args = parser.parse_args()

    paths = {
        "elevation": DATA / "Site01_final_adj_5mpp_surf.tif",
        "measurement_count": DATA / "Site01_final_adj_5mpp_ldec.tif",
        "elevation_uncertainty": DATA / "Site01_final_adj_5mpp_toterr.tif",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise SystemExit(f"Missing {label}: {path}")

    with rasterio.open(paths["elevation"]) as ds:
        if not ds.crs:
            raise SystemExit("DEM has no coordinate reference system")
        if not ds.crs.is_projected:
            raise SystemExit("Expected projected Site01 DEM")
        dem = ds.read(1, masked=True).astype(float).filled(np.nan)
        tfm, crs = ds.transform, ds.crs
        grid_shape = dem.shape
        x, y = convert_coordinates(SOURCE_CRS, crs, [LON], [LAT])[:2]
        x, y = float(x[0]), float(y[0])
        origin_row, origin_col = ds.index(x, y)
        if not (0 <= origin_row < ds.height and 0 <= origin_col < ds.width):
            raise SystemExit("Representative coordinate is outside the DEM")
        ground = float(dem[origin_row, origin_col])
    extra_layers = {}
    for label in ("measurement_count", "elevation_uncertainty"):
        with rasterio.open(paths[label]) as ds:
            if ds.shape != grid_shape or ds.transform != tfm or ds.crs != crs:
                raise SystemExit(f"Grid mismatch for {label}")
            extra_layers[label] = ds.read(1, masked=True).astype(float).filled(np.nan)

    records = calculate_horizon(
        dem, tfm, x, y, args.max_distance_m, args.sample_step_m,
        args.azimuth_step_deg, args.observer_height_m, MOON_RADIUS_M,
        counts=extra_layers["measurement_count"],
        errors=extra_layers["elevation_uncertainty"],
    )
    angles = [r["horizon_angle_deg"] for r in records if r["horizon_angle_deg"] is not None]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    report = {
        "analysis_type": "DEM-limited terrain horizon prototype",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "site": "Site01", "site_name": "Connecting Ridge",
        "reference_latitude_deg": LAT, "reference_longitude_deg": LON,
        "reference_xy_projected_m": [x, y],
        "reference_row_col": [origin_row, origin_col],
        "reference_elevation_m": ground,
        "crs_wkt": crs.to_wkt(),
        "settings": {
            "max_distance_m": args.max_distance_m,
            "sample_step_m": args.sample_step_m,
            "azimuth_step_deg": args.azimuth_step_deg,
            "observer_height_m": args.observer_height_m,
            "moon_radius_m": MOON_RADIUS_M,
            "sampling": "nearest-cell sampling along projected XY rays",
            "azimuth_reference": "clockwise from projected grid +Y, NOT geographic true north",
            "curvature": "spherical local radial geometry",
        },
        "summary": {
            "azimuths_attempted": len(records),
            "azimuths_with_results": len(angles),
            "min_angle_deg": min(angles) if angles else None,
            "max_angle_deg": max(angles) if angles else None,
            "mean_angle_deg": sum(angles) / len(angles) if angles else None,
            "boundary_truncated_azimuths": sum(r["boundary_truncated"] for r in records),
            "directions_with_missing_dem_samples": sum(r["missing_elevation_samples"] > 0 for r in records),
            "controlling_pixels_without_lola_spots": sum(
                r["controlling_measurement_count"] == 0
                for r in records if r["controlling_measurement_count"] is not None),
        },
        "limitations": [
            "Only terrain inside Site01 DEM and selected max distance is considered; distant obstructing terrain is unknown.",
            "Angles use the projected-grid directions and are NOT true lunar geodetic azimuths.",
            "The projection-space sample distance approximates lunar surface arc distance.",
            "DEM elevations are treated as radial heights relative to nominal lunar spherical radius: verify datum before scientific use.",
            "Nearest-cell samples may miss narrow obstacles; this is an exploratory estimate, not a certified horizon.",
            "LOLA count 0 implies interpolated DEM; the count and uncertainty metadata do not prove horizon accuracy.",
            "Reported elevation RMS error is at the controlling pixel only, NOT propagated to horizon angle.",
            "No Sun position, illumination, communication visibility, or landing-safety assessment has been calculated.",
        ],
        "angles": records,
    }
    # Keep analyses with different radii distinct, instead of overwriting plots.
    radius = args.max_distance_m
    radius_label = f"{radius / 1000:g}km" if radius >= 1000 else f"{radius:g}m"
    basename = f"Site01_horizon_{radius_label}"
    out_json = OUTPUT / f"{basename}.json"

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    az = [r["grid_azimuth_deg"] for r in records]
    an = [np.nan if r["horizon_angle_deg"] is None else r["horizon_angle_deg"] for r in records]
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.plot(az, an, linewidth=1.4)
    ax.axhline(0, linewidth=0.8, color="grey")
    ax.set(xlabel="Grid azimuth clockwise from +Y (degrees; NOT true north)",
           ylabel="Maximum sampled terrain elevation angle (degrees)",
           title="Connecting Ridge (Site01) — DEM-limited terrain horizon")
    ax.set_xlim(0, 360)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    out_png = OUTPUT / f"{basename}.png"
    try:
        fig.savefig(out_png, dpi=160)
    except OSError as exc:
        raise SystemExit(
            f"Cannot save {out_png}: {exc}\n"
            "Close any image viewer or OneDrive process holding this file open, "
            "then rerun the command."
        ) from exc
    finally:
        plt.close(fig)

    # Write JSON after the PNG succeeds so a failed plot cannot leave
    # a new JSON paired with an outdated PNG.
    out_json.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")

    print("===== SELENEKTO SITE01 TERRAIN HORIZON =====")
    print(f"Reference grid cell: row {origin_row}, column {origin_col}")
    print(f"Reference DEM elevation: {ground:.3f} m")
    print(f"Direction step: {args.azimuth_step_deg:g}° | Distance step: {args.sample_step_m:g} m")
    print(f"Search radius: {args.max_distance_m:g} m | Eye height above surface: {args.observer_height_m:g} m")
    print(f"Directions with results: {len(angles)}/{len(records)}")
    if angles:
        print(f"Terrain horizon angle range: {min(angles):.3f}° to {max(angles):.3f}°")
    print(f"Grid-edge truncated directions: {report['summary']['boundary_truncated_azimuths']}")
    print(f"Controlling cells with 0 observed LOLA spots: {report['summary']['controlling_pixels_without_lola_spots']}")
    print(f"JSON: {out_json.relative_to(ROOT)}")
    print(f"Plot: {out_png.relative_to(ROOT)}")
    print("WARNING: Local DEM-limited, grid-relative prototype; NOT solar illumination or landing safety.")


if __name__ == "__main__":
    main()
