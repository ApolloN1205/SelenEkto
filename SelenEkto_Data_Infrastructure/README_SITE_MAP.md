# SelenEkto — Site01 Interactive Terrain Map

This is a separate desktop **feature**, not a replacement for the solar viewer and not the finished multi-site navigator.

## What it does
- Loads the five existing NASA PGDA Site01 GeoTIFFs from `data/raw/lola/Site01/`.
- Shows a downsampled terrain-map preview. Inspect at full native 5 m/pixel resolution by clicking: the five cell values are read directly from the original raster.
- Switch among elevation, slope, elevation uncertainty, slope uncertainty, LOLA measurement count.
- Save multiple clicked candidate cells in a local table; export cell coordinates and values to CSV.
- Launch your existing terrain/solar viewer from the map.

## Install
Extract ZIP **into the existing outer `SelenEkto_Data_Infrastructure` folder**. Nothing in the ZIP replaces a pre-existing script. Verify first:

```powershell
Test-Path .\scripts\launch_site_map.py
Test-Path .\src\selenekto_data\site_map.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_site_map.py
```

If your package isn't found, choose its location interactively and extract with `Expand-Archive`; do not assume it is in Downloads.

## Limitations
- Only Site01 has been acquired. We **do not** pretend to map the whole lunar south pole or compare other NASA DEM sites yet.
- Selected cells are exploratory candidate points, NOT certified landing locations. There is no safety ranking, travel-route analysis or sunlight at each selected point yet.
- Map X and Y are lunar south-polar projected metres, NOT longitude/latitude.
- The current saved horizon and solar results apply to one published representative Site01 point (row 1599 col 1600). They must NOT be reused as if computed for arbitrary clicked cells.
- Low-count pixels may be interpolated; elevation RMS is not a confidence interval. The display is scientific exploration only.
