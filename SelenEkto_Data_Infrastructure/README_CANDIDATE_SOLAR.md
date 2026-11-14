# SelenEkto — Candidate solar timelines and adjustable comparison (experimental)

## What this adds

- Every selected Site01 candidate gets **its own** JPL Horizons Sun-position request using the projected cell centre converted to lunar latitude/longitude.
- Every candidate is compared to **its own saved 360° horizon**, not Site01's reference-point horizon.
- Produces a time-series clearance plot, CSV comparison, and detailed JSON with provenance and limitations.
- Scores can be adjusted with three weights. Scores are comparative preferences **only**; there is no forced winner, site-selection recommendation or safety certification.
- No changes to your working map, existing solar viewer, or DEM files.

## Prerequisites

1. The `SelenEkto_Map_Fix_And_Candidate_Analysis` ZIP must have been extracted and its map workflow confirmed.
2. Select two or more map cells, click **Add selected cell**, and click **Analyze candidate horizons** (or export CSV and run `scripts/analyze_candidate_horizons.py`).
3. Confirm the generated file exists:

   `data/processed/candidate_horizons/Site01/Site01_candidate_horizons_500m.json`

4. Installed Python packages: `pyproj`, `rasterio`, `numpy`, `matplotlib` (already used by prior milestones), plus internet access to NASA/JPL Horizons.

## Run from SelenEkto_Data_Infrastructure

```powershell
Test-Path .\scripts\analyze_candidate_solar.py
Test-Path .\data\processed\candidate_horizons\Site01\Site01_candidate_horizons_500m.json
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\analyze_candidate_solar.py --date 2026-11-14 --hours 72 --interval-min 60
```

For different weight priorities:

```powershell
.\.venv\Scripts\python.exe .\scripts\analyze_candidate_solar.py --date 2026-11-14 --sun-weight 4 --slope-weight 2 --uncertainty-weight 1
```

Outputs appear at:

`data/processed/candidate_solar/Site01/2026-11-14/`

- `candidate_solar_clearance.png`
- `candidate_solar_summary.csv`
- `candidate_solar_comparison.json`

## Interpreting the result

- **Clearance (degrees)** = actual queried Sun altitude − the selected cell's modelled terrain-horizon angle in the same direction. Positive is above the modelled local skyline.
- **Clear-sample fraction** = proportion of sampled timestamps where the Sun's *centre* is above the modelled local skyline. It is *not* continuously illuminated hours and does not capture solar-disc radius, scattering, eclipses, or unmodelled remote ridges.
- **Score** = weighted average of relative normalised candidate features: larger clear-sample fraction is preferred, smaller slope and smaller elevation RMS error are preferred. Values and weight choices are in the JSON. Changing the candidate list changes relative scores.
- Candidate horizon uncertainty was not propagated in this package; initial Site01 reference uncertainty must **not** be applied to all candidates.

## Known limitations

NASA/JPL requests need an internet connection. The calculation depends on a **preliminary** Moon spherical lat/lon and raster projection conversion and approximate grid orientation; independent MOON_ME/DE421 frame validation is still required. The source raster is regional and horizon searches are local only. Unknown or invalid inputs are rejected rather than silently replaced with data from another candidate. Outputs are not landing-safety results.

## Next integration

Bring map, terrain comparison and timelines into a single tabbed app; add dataset discovery for additional PGDA site regions and validate those regions individually.
