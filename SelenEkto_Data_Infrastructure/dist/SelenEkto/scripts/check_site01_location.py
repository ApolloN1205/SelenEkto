"""Check the NASA representative centre for Site01 against the PGDA DEM grid.

This is a coordinate/grid consistency check, NOT a validated landing-site
position or a terrain-horizon calculation. It uses the lunar spherical radius
shown in the user's Site01 GeoTIFF WKT and the published Data Book coordinates.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import rasterio
from rasterio.warp import transform as transform_coordinates

BASE = Path("data/raw/lola/Site01")
OUTPUT = Path("data/processed/site_profiles/Site01_location_check.json")

# NASA Lunar Surface Data Book, 2025, Appendix A, Table A2.1-1.
# These are representative region-centre coordinates, NOT an exact landing site.
SITE_NAME = "Connecting Ridge"
SITE_ID = "Site01"
LATITUDE_DEG = -89.4632
LONGITUDE_AS_PUBLISHED_DEG = -137.49
COORDINATE_SOURCE = (
    "NASA Lunar Surface Data Book, M2M-30044, Baseline, 2025-03-18, "
    "Appendix A, Table A2.1-1, p.75"
)

# The source GeoTIFF WKT supplied by the user describes a lunar sphere with
# radius 1,737,400 m. Its target CRS is read directly from the GeoTIFF.
LUNAR_SPHERE_GEOGRAPHIC_CRS = (
    "+proj=longlat +R=1737400 +no_defs +type=crs"
)

LAYERS = {
    "elevation": "Site01_final_adj_5mpp_surf.tif",
    "measurement_count": "Site01_final_adj_5mpp_ldec.tif",
    "elevation_uncertainty": "Site01_final_adj_5mpp_toterr.tif",
    "slope": "Site01_final_adj_5mpp_slp.tif",
    "slope_uncertainty": "Site01_final_adj_5mpp_slperr.tif",
}


def main() -> int:
    dem_path = BASE / LAYERS["elevation"]
    if not dem_path.is_file():
        raise FileNotFoundError(f"Required DEM not found: {dem_path}")

    with rasterio.open(dem_path) as dem:
        if dem.crs is None:
            raise ValueError("DEM has no CRS; refusing to transform coordinates.")

        # Use the published negative longitude as supplied. JPL's lunar
        # longitude conventions allow negative east-longitude values to
        # represent westward longitudes; the Data Book value is preserved.
        x_values, y_values = transform_coordinates(
            LUNAR_SPHERE_GEOGRAPHIC_CRS,
            dem.crs,
            [LONGITUDE_AS_PUBLISHED_DEG],
            [LATITUDE_DEG],
        )
        x = float(x_values[0])
        y = float(y_values[0])

        row, col = dem.index(x, y)
        inside = 0 <= row < dem.height and 0 <= col < dem.width
        if not inside:
            raise ValueError(
                "Published representative centre does not fall inside the "
                "Site01 DEM using the stated spherical transformation. "
                "Check longitude convention and coordinate-frame assumptions."
            )

        centre_x, centre_y = dem.xy(row, col, offset="center")
        offset_m = math.hypot(float(centre_x) - x, float(centre_y) - y)
        elevation_value = dem.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
        if dem.nodata is not None and elevation_value == dem.nodata:
            elevation_value = None
        elif not math.isfinite(float(elevation_value)):
            elevation_value = None
        else:
            elevation_value = float(elevation_value)

        target_crs = dem.crs
        target_transform = dem.transform
        target_bounds = dem.bounds
        grid_reference = {
            "width": dem.width,
            "height": dem.height,
            "crs_wkt": dem.crs.to_wkt(),
            "transform": list(dem.transform)[:6],
            "bounds": [dem.bounds.left, dem.bounds.bottom, dem.bounds.right, dem.bounds.top],
            "pixel_resolution_metres": [abs(dem.res[0]), abs(dem.res[1])],
        }

    layer_checks = {}
    for layer_name, filename in LAYERS.items():
        path = BASE / filename
        if not path.is_file():
            layer_checks[layer_name] = {"present": False, "file": filename}
            continue
        with rasterio.open(path) as ds:
            aligned = (
                ds.width == grid_reference["width"]
                and ds.height == grid_reference["height"]
                and ds.crs == target_crs
                and ds.transform == target_transform
                and ds.bounds == target_bounds
            )
            value = ds.read(1, window=((row, row + 1), (col, col + 1)))[0, 0]
            if ds.nodata is not None and value == ds.nodata:
                value = None
            elif not math.isfinite(float(value)):
                value = None
            else:
                value = float(value)
            layer_checks[layer_name] = {
                "present": True,
                "file": filename,
                "grid_matches_dem": bool(aligned),
                "value_at_region_centre_pixel": value,
            }
            if not aligned:
                raise ValueError(f"Raster grid mismatch in {filename}")

    # Diagnostic only: compare the opposite longitude sign. Do not use this
    # to silently choose a convention; preserve the published value above.
    opposite_xs, opposite_ys = transform_coordinates(
        LUNAR_SPHERE_GEOGRAPHIC_CRS,
        target_crs,
        [-LONGITUDE_AS_PUBLISHED_DEG],
        [LATITUDE_DEG],
    )
    opposite_x, opposite_y = float(opposite_xs[0]), float(opposite_ys[0])
    opposite_row, opposite_col = dem.index(opposite_x, opposite_y)
    opposite_inside = (
        0 <= opposite_row < grid_reference["height"]
        and 0 <= opposite_col < grid_reference["width"]
    )

    result = {
        "site_id": SITE_ID,
        "site_name": SITE_NAME,
        "coordinate_source": COORDINATE_SOURCE,
        "coordinate_role": "representative_region_centre_not_exact_landing_site",
        "published_latitude_deg": LATITUDE_DEG,
        "published_longitude_deg": LONGITUDE_AS_PUBLISHED_DEG,
        "longitude_value_preserved_as_published": True,
        "source_geographic_crs_assumption": LUNAR_SPHERE_GEOGRAPHIC_CRS,
        "target_crs_description": "Read from the original Site01 LDEM GeoTIFF",
        "projected_coordinate_metres": {"x": x, "y": y},
        "containing_pixel": {"row": int(row), "column": int(col)},
        "pixel_centre_metres": {"x": float(centre_x), "y": float(centre_y)},
        "distance_from_projected_coordinate_to_pixel_centre_metres": offset_m,
        "representative_centre_inside_dem": bool(inside),
        "elevation_at_containing_pixel_metres": elevation_value,
        "opposite_longitude_diagnostic": {
            "opposite_longitude_deg": -LONGITUDE_AS_PUBLISHED_DEG,
            "projected_x_metres": opposite_x,
            "projected_y_metres": opposite_y,
            "inside_dem": bool(opposite_inside),
            "note": "Diagnostic only; does not establish an alternate convention.",
        },
        "grid": grid_reference,
        "layers_at_centre_pixel": layer_checks,
        "scientific_status": "PRELIMINARY_COORDINATE_GRID_CONSISTENCY_CHECK",
        "limitations": [
            "The Data Book coordinate is a representative region centre, not an exact landing coordinate.",
            "This check does not independently validate the full MOON_ME/DE421 frame transformation.",
            "Confirm pixel-registration convention and geodetic/planetocentric definition against the PGDA README before horizon calculations.",
            "No horizon, solar illumination, Earth visibility, or communications result is calculated.",
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("===== SELENEKTO SITE01 COORDINATE CHECK =====")
    print(f"Region: {SITE_NAME} ({SITE_ID})")
    print(f"Published latitude/longitude: {LATITUDE_DEG}, {LONGITUDE_AS_PUBLISHED_DEG}")
    print(f"Projected X/Y: {x:.3f} m, {y:.3f} m")
    print(f"Containing pixel: row {row}, column {col}")
    print(f"Distance to pixel centre: {offset_m:.3f} m")
    print(f"Representative centre inside DEM: {inside}")
    print(f"Elevation at containing pixel: {elevation_value}")
    print("All available layers align with the DEM: True")
    print(f"Diagnostic opposite longitude inside DEM: {opposite_inside}")
    print(f"Report: {OUTPUT}")
    print("NOTE: This is a preliminary grid check, not a validated horizon calculation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
