# SelenEkto reusable terrain profile — installation

This add-on creates a reusable terrain-profile function for a PGDA site. It reads the five registered LOLA rasters, checks their integrity and grid alignment, calculates descriptive statistics and writes a JSON site profile.

## Install

Extract this ZIP **into the existing `SelenEkto_Data_Infrastructure` folder**, merging its `src`, `scripts`, and `tests` directories. It adds new files only:

- `src/selenekto_data/terrain.py`
- `scripts/analyze_site.py`
- `tests/test_terrain_analysis.py`

Do not extract it into the outer Git repository root; the paths in the ZIP are relative to the data-infrastructure folder.

## Run tests

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

## Build Site01 profile

```powershell
.\.venv\Scripts\python.exe .\scripts\analyze_site.py --site Site01
```

Expected output:

`data/processed/site_profiles/Site01_terrain_profile.json`

## Important scientific boundary

The report contains whole-raster descriptive statistics and provenance. It checks that the five rasters share dimensions, CRS, transform and bounds. It does **not** calculate a local horizon, lighting, Earth visibility, landing safety, solar power, or communications link performance.

The catalogue's region-centre coordinates are included as reference metadata only. This module does not convert latitude/longitude to DEM X/Y and does not use those reference points as a precision landing target. That transformation requires a separately verified lunar reference-frame and projection workflow.

Raw source GeoTIFFs are read-only. The report is written to `data/processed/site_profiles/`.
