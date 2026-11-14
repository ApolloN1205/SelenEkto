# SelenEkto — Unified multi-region milestone

This add-on does NOT overwrite the working `launch_dashboard.py`, `launch_multiregion.py`, Site01 analysis scripts or downloaded NASA data.

## What it adds
- 27 NASA PGDA catalogue regions, dynamically enabled when all five real raster layers are installed
- Dark region/layer selectors (Tk OptionMenu) with readable white text
- Five NASA map layers: elevation, slope, elevation RMS, slope RMS and LOLA count
- Named and renamed candidates from *any* installed region, exported with region identifiers
- Interactive terrain-slope comparison between candidates across different regions
- Independent local DEM horizon for each candidate (up to 12 per analysis)
- Optional real JPL Horizons request for each candidate, with dated solar visibility and user-adjustable preference weights
- A resumable bulk download that skips existing validated TIFFs and never overwrites existing files

## Installation
From PowerShell in `SelenEkto_Data_Infrastructure`, extract the add-on zip to `.`.
Verify:
```
Test-Path .\scripts\launch_unified_dashboard.py
Test-Path .\scripts\download_all_pgda_regions.py
Test-Path .\src\selenekto_data\unified_regions.py
```
Then:
```
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_unified_dashboard.py
```

## Download NASA regions
Six original sites are `Site01 Site04 Site07 Site11 Site20 Site23`.
To start with those six:
```
.\.venv\Scripts\python.exe .\scripts\download_all_pgda_regions.py --regions Site01 Site04 Site07 Site11 Site20 Site23
```
For **all 27 PGDA catalogue entries** (a large download potentially involving gigabytes and many hours depending on connection; use available local storage):
```
.\.venv\Scripts\python.exe .\scripts\download_all_pgda_regions.py --all
```
The downloader is intentionally sequential. Completed files remain when interrupted, and the next run skips them after raster validation. The current `--all` operation is a collection of original georeferenced GeoTIFFs, not the full point cloud, clones, or polygon files. The app never claims those additional products are present.

## Use
Launch dashboard; choose a region and a layer, click the map, Add candidate, assign a name. Switch regions and add more candidates. Compare shows actual slopes from the chosen cells. On Solar + Horizons, run the local horizons first or the live solar + horizons process. Open results for exported JSON, CSV and PNG. Live solar requests require internet and may fail if Horizons refuses requests. The separate console displays full errors.

## Science notes
All candidate profiles use a finite-radius, grid-relative 360° horizon and approximate spherical lunar geometry, with no distant-terrain completeness guarantee. NASA provided DEM RMS error is not itself the solar-angle uncertainty. The code uses the existing project's `selenekto_data.horizon`, `.solar`, and `.candidate_solar` components. Solar directions, lunar projection conventions and geodetic assumptions still need independent validation. Relative scores are user-defined trade-offs, NOT assessed safe landing sites.

## Data source
https://pgda.gsfc.nasa.gov/products/78
https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/
