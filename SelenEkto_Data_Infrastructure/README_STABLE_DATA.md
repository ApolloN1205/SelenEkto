# SelenEkto stable launcher + all-region JSON profiles

This add-on **does not overwrite existing dashboard code or GeoTIFFs**. It contains a safe launcher and an offline JSON profile builder.

## Install

Extract the ZIP into the **outer** `SelenEkto_Data_Infrastructure` directory. Check:

```powershell
Test-Path .\scripts\build_all_region_json.py
Test-Path .\scripts\launch_selenekto_safe.py
Test-Path .\src\selenekto_data\region_profiles.py
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_region_profiles.py -q
```

Generate JSON profiles for **all 27 catalogue entries** (including files missing or invalid in your local download):

```powershell
.\.venv\Scripts\python.exe .\scripts\build_all_region_json.py
```

This will take time: it must inspect up to 135 large rasters. The script prints progress after each region. If a region is missing or contains an invalid layer, it still writes an explicit JSON file but marks the region as incomplete/invalid. **A JSON file does not mean the region is usable.**

Outputs (inside the project):

- `data/catalog/region_profiles/Site01_terrain_profile.json`
- `data/catalog/region_profiles/Site04_terrain_profile.json` etc.
- `data/catalog/region_profiles/regions_index.json`
- `data/catalog/region_profiles/regions_index.csv`

Run safe launcher:

```powershell
.\.venv\Scripts\python.exe .\scripts\launch_selenekto_safe.py
```

The launcher opens immediately without reading NASA GeoTIFFs. Select the earlier integrated dashboard (confirmed working) or the repaired one. It captures Python output to `data/processed/logs` and does not modify prior launchers.

## Git layout

Commit small human-readable metadata **after reviewing it**:

```powershell
# From the outer infrastructure directory
# Confirm JSON directory is not ignored and count generated profiles
Get-ChildItem .\data\catalog\region_profiles\*_terrain_profile.json | Measure-Object
# From the Git repository root (one level above the infrastructure directory):
cd ..
git status --short
```

Source GeoTIFFs are the true data and are typically ~tens of megabytes each, so 135 rasters could be several GB. They should normally stay local or in a separate verifiable data release/object store, with source URLs, manifests, checksums and a reproducible download process. **Do not `git add -f` raw GeoTIFFs to the normal repository**. If the team deliberately wants versioned binary data, research Git LFS/storage limits first. Do not treat the JSON profiles as a replacement for rasters.

The profile matches the broad Site01 JSON shape (`site_code`, `grid`, `layers`, `statistics`), but exact medians/percentiles of the full raster are *not* calculated: the generated JSON labels them as overview-sampled approximations. Other scalar statistics and valid/missing counts are computed over all pixels.

## Black-screen diagnosis

A black window can be caused by plotting/backend startup, a long blocking operation, or an uncaught exception; it cannot be diagnosed from a report of a black window alone. The safe launcher avoids heavy startup and records output, but **does not claim to fix every GUI bug**. If a dashboard is black, close it and send the terminal traceback or `data/processed/logs/<launcher>.log`. If the old integrated dashboard works, use it while the experimental dashboard is repaired.
