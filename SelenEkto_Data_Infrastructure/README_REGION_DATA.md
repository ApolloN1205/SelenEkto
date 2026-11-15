# SelenEkto 2.0 — Readable JSON and numeric comparisons

This additive package does **not** overwrite your previously working `launch_selenekto_v2.py`. The new launcher is `launch_selenekto_v2_data.py`.

## Requirements

- Existing SelenEkto infrastructure with `data/catalog/region_profiles/*_terrain_profile.json` from `build_all_region_json.py`
- Existing PySide6 dashboard (`src/selenekto_v2/core.py`)
- Existing Python virtual environment with PySide6, matplotlib, numpy and rasterio

## Install

From `SelenEkto_Data_Infrastructure`:

1. Extract this ZIP into the current folder (merging `scripts/`, `src/` and `tests/`).
2. Verify: `Test-Path .\scripts\prepare_region_data.py` and `Test-Path .\scripts\launch_selenekto_v2_data.py`.
3. If needed, regenerate original raster-derived profiles: `.\.venv\Scripts\python.exe .\scripts\build_all_region_json.py`.
4. Enrich existing profiles (does not rescan massive TIFF files): `.\.venv\Scripts\python.exe .\scripts\prepare_region_data.py`.
5. Test: `.\.venv\Scripts\python.exe -m pytest tests -q`.
6. Launch: `.\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2_data.py`.

## What you get

- Original 27 (if present) JSON files retain `layers`, `grid`, `errors`, `availability`, `dataset_provenance` and original full-raster statistics.
- Additional `readable_metrics` object in each profile has consistent names, numeric values, units, missing-status indicators and valid coverage.
- `regions_comparable.csv` for Excel, GitHub and reports, with one row per region.
- In the new PySide6 launcher, the **Compare** page has a dropdown to compare one candidate metric at a time: slope, elevation, elevation RMS, slope RMS or LOLA counts. This avoids mixing degrees with metres on a single axis.
- **Compare ALL region JSON statistics** opens a separate table of all region summaries and a graph of a chosen summary metric. Use Ctrl+click rows to graph a subset.
- Existing side-by-side map comparison and named candidate store remain available.

## Reading a region JSON

```
{
  "site_code": "Site01",
  "availability": "ready",
  "layers": {"slope": {"statistics": {"mean": 12.5977}}},
  "readable_metrics": {
    "slope": {
      "status": "ready", "units": "degrees", "mean": 12.5977,
      "minimum": 0.0, "maximum": 64.5882,
      "valid_coverage_percent": 100.0
    }
  }
}
```

The numbers above illustrate fields using previously observed Site01 outputs; **the script reads your own real JSON** rather than hardcoding example values.

If a layer is absent, its numeric summary is `null`, *not zero*. A JSON entry marked `incomplete` is not suitable for terrain analysis. Median and percentiles use sampled overviews in the original builder; mean, standard deviation, min/max and counts are derived from full rasters. Your 27 profiles may include incomplete regions; a profile file is not evidence that all five source rasters are usable.

## Data storage

Commit the compact JSON profiles and `regions_comparable.csv` to Git. Keep the large original GeoTIFF rasters local and document reproducible downloads. JSON profiles are summaries: the original TIFFs are still needed for pixel selection and horizon modelling. No changes to your solar calculations are made here.
