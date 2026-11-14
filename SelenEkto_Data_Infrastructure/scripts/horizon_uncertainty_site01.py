"""SelenEkto Site01: deterministic +/- 1 reported elevation RMS sensitivity.

Run from the SelenEkto_Data_Infrastructure root:
  Run with your virtualenv Python from the infrastructure root.

This is NOT a statistical confidence interval, bound on actual error, or landing-safety claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import transform as reproject_coordinates

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from selenekto_data.horizon import calculate_horizon, MOON_RADIUS_M  # noqa: E402

LAT, LON = -89.4632, -137.49
SOURCE_CRS = "+proj=longlat +R=1737400 +no_defs +type=crs"
RAW = ROOT / "data" / "raw" / "lola" / "Site01"
OUT = ROOT / "data" / "processed" / "horizon" / "Site01"


def run_sensitivity(dem, errors, transform, x, y, *, radius_m=5000.0,
                    step_m=10.0, azimuth_step_deg=1.0, observer_height_m=0.0):
    """Calculate baseline and two deliberately conservative opposing scenarios.

    high: origin elevation decreases by its reported RMS, all other cells rise
    by their RMS. low: origin rises while all other cells fall. These are
    illustrative scenarios; RMS values do not establish hard uncertainty bounds.
    """
    from rasterio.transform import rowcol

    if dem.shape != errors.shape:
        raise ValueError("Elevation and uncertainty grids have different shapes")
    r, c = rowcol(transform, x, y)
    if not (0 <= r < dem.shape[0] and 0 <= c < dem.shape[1]):
        raise ValueError("Observer is outside raster")
    if not np.isfinite(dem[r, c]):
        raise ValueError("Missing DEM at observer")
    if not np.isfinite(errors[r, c]) or errors[r, c] < 0:
        raise ValueError("Missing or negative elevation uncertainty at observer")
    missing_error = np.isfinite(dem) & (~np.isfinite(errors) | (errors < 0))
    if missing_error.any():
        raise ValueError(f"Missing/invalid uncertainty at {int(missing_error.sum())} valid DEM cells")

    kwargs = dict(max_distance_m=radius_m, sample_step_m=step_m,
                  azimuth_step_deg=azimuth_step_deg, observer_height_m=observer_height_m,
                  moon_radius_m=MOON_RADIUS_M)
    baseline = calculate_horizon(dem, transform, x, y, **kwargs)
    higher = dem + errors
    lower = dem - errors
    # Make observer move in the opposite direction to the candidate obstacles.
    higher[r, c] = dem[r, c] - errors[r, c]
    lower[r, c] = dem[r, c] + errors[r, c]
    high_records = calculate_horizon(higher, transform, x, y, **kwargs)
    low_records = calculate_horizon(lower, transform, x, y, **kwargs)

    entries = []
    for a, lo, hi in zip(baseline, low_records, high_records):
        b, l, h = (v["horizon_angle_deg"] for v in (a, lo, hi))
        if b is not None and l is not None and h is not None and not (l - 0.000002 <= b <= h + 0.000002):
            raise RuntimeError("Scenario ordering unexpectedly failed")
        entries.append({
            "grid_azimuth_deg": a["grid_azimuth_deg"],
            "baseline_angle_deg": b,
            "low_scenario_angle_deg": l,
            "high_scenario_angle_deg": h,
            "low_shift_deg": round(l - b, 6) if b is not None and l is not None else None,
            "high_shift_deg": round(h - b, 6) if b is not None and h is not None else None,
            "baseline_controlling_distance_m": a["controlling_distance_m"],
            "low_controlling_distance_m": lo["controlling_distance_m"],
            "high_controlling_distance_m": hi["controlling_distance_m"],
            "controlling_cell_changed_low": (
                (lo["controlling_row"], lo["controlling_col"]) !=
                (a["controlling_row"], a["controlling_col"])),
            "controlling_cell_changed_high": (
                (hi["controlling_row"], hi["controlling_col"]) !=
                (a["controlling_row"], a["controlling_col"])),
        })
    return entries, float(errors[r, c])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-distance-m", type=float, default=5000.0)
    parser.add_argument("--sample-step-m", type=float, default=10.0)
    parser.add_argument("--azimuth-step-deg", type=float, default=1.0)
    parser.add_argument("--observer-height-m", type=float, default=0.0)
    args = parser.parse_args()
    paths = {
        "dem": RAW / "Site01_final_adj_5mpp_surf.tif",
        "err": RAW / "Site01_final_adj_5mpp_toterr.tif",
    }
    for path in paths.values():
        if not path.is_file():
            raise SystemExit(f"Missing input raster: {path}")
    with rasterio.open(paths["dem"]) as ds:
        if not ds.crs or not ds.crs.is_projected:
            raise SystemExit("DEM projected CRS required")
        dem = ds.read(1, masked=True).astype("float64").filled(np.nan)
        tfm, crs, shape = ds.transform, ds.crs, ds.shape
    with rasterio.open(paths["err"]) as ds:
        if ds.shape != shape or ds.transform != tfm or ds.crs != crs:
            raise SystemExit("Uncertainty layer does not share DEM grid")
        errors = ds.read(1, masked=True).astype("float64").filled(np.nan)
    x_list, y_list = reproject_coordinates(SOURCE_CRS, crs, [LON], [LAT])[:2]
    entries, origin_rms = run_sensitivity(
        dem, errors, tfm, float(x_list[0]), float(y_list[0]),
        radius_m=args.max_distance_m, step_m=args.sample_step_m,
        azimuth_step_deg=args.azimuth_step_deg,
        observer_height_m=args.observer_height_m,
    )
    shifts = [max(abs(e["low_shift_deg"]), abs(e["high_shift_deg"]))
              for e in entries if e["low_shift_deg"] is not None]
    max_shift = max(shifts) if shifts else None
    median_shift = float(np.median(shifts)) if shifts else None
    changed_low = sum(e["controlling_cell_changed_low"] for e in entries)
    changed_high = sum(e["controlling_cell_changed_high"] for e in entries)
    report = {
        "analysis_type": "Site01 DEM horizon deterministic elevation-RMS sensitivity scenarios",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "site": "Site01", "reference_latitude_deg": LAT, "reference_longitude_deg": LON,
        "settings": vars(args), "observer_reported_elevation_rms_m": origin_rms,
        "method": (
            "For the high scenario, move each non-observer DEM elevation up by one "
            "reported elevation RMS and the observer cell down by one RMS. "
            "Reverse for the low scenario. Recalculate the horizon independently "
            "for each full raster, allowing the controlling cell to change."
        ),
        "summary": {
            "directions": len(entries), "max_absolute_shift_deg": max_shift,
            "median_max_absolute_shift_deg": median_shift,
            "changed_controlling_cells_low": changed_low,
            "changed_controlling_cells_high": changed_high,
        },
        "limitations": [
            "These are deterministic +/- 1 reported RMS scenarios, NOT confidence intervals or guaranteed error bounds.",
            "DEM interpolation and spatially correlated errors may not be represented adequately by per-cell RMS.",
            "The DEM grid, coordinate approximation, 5m cells and ray sampling are unchanged; systematic errors are not tested.",
            "Only terrain within the configured radius and Site01 footprint is tested; distant obstructions are unknown.",
            "Grid azimuth is not geographic true north; no solar illumination or landing safety is calculated.",
        ],
        "directions": entries,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    radius = args.max_distance_m
    radius_label = f"{radius / 1000:g}km" if radius >= 1000 else f"{radius:g}m"
    stem = f"Site01_horizon_uncertainty_{radius_label}"

    # Distinct output names; avoid overwriting any baseline horizon files.
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    xs = [e["grid_azimuth_deg"] for e in entries]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(xs, [e["baseline_angle_deg"] for e in entries], label="Baseline", linewidth=1.3)
    ax.plot(xs, [e["low_scenario_angle_deg"] for e in entries], label="Low scenario", alpha=0.8)
    ax.plot(xs, [e["high_scenario_angle_deg"] for e in entries], label="High scenario", alpha=0.8)
    ax.set(xlabel="Projected-grid azimuth (degrees; not true north)",
           ylabel="Terrain horizon angle (degrees)",
           title="Site01: deterministic +/- elevation RMS sensitivity (NOT confidence interval)")
    ax.set_xlim(0, 360)
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    image_path = OUT / f"{stem}.png"
    try:
        fig.savefig(image_path, dpi=150)
    finally:
        plt.close(fig)
    json_path = OUT / f"{stem}.json"
    json_path.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")

    print("===== SELENEKTO SITE01 HORIZON UNCERTAINTY SENSITIVITY =====")
    print(f"Reference cell elevation RMS: {origin_rms:.4f} m")
    print(f"Directions analysed: {len(entries)}")
    print(f"Max absolute scenario angle shift: {max_shift:.4f} degrees")
    print(f"Median per-direction maximum absolute shift: {median_shift:.4f} degrees")
    print(f"Changed controlling cells (low scenario): {changed_low}")
    print(f"Changed controlling cells (high scenario): {changed_high}")
    print(f"JSON: {json_path.relative_to(ROOT)}")
    print(f"PNG:  {image_path.relative_to(ROOT)}")
    print("WARNING: RMS perturbation scenarios are NOT statistical confidence intervals or proven bounds.")


if __name__ == "__main__":
    main()
