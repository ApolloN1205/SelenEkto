# SelenEkto — real JPL solar positions (experimental)

The previous desktop viewer is **one feature**, not the final SelenEkto. This add-on integrates dated Sun positions into the viewer without changing its terrain graph or CSV workflow.

## What is new
- UTC calendar start date, duration (hours), sample interval (minutes)
- Sun azimuth and elevation requested from **JPL Horizons**, target Sun `10`, observer a surface coordinate on Moon `coord@301`, observer table `QUANTITIES='4'` (azimuth and elevation)
- Local geographic north converted into DEM **projected-grid** azimuth by spherical Moon geodesic plus projection
- Comparison of Sun elevation against saved terrain-horizon and ±1 RMS deterministic scenarios
- Interactive timeline window and saved `data/processed/solar/Site01/Site01_solar_timeline.json` / `.csv`
- Source request settings and modelling limitations saved in JSON

## Install
Extract ZIP into the already existing outer `SelenEkto_Data_Infrastructure` directory, **merging folders**. It deliberately replaces `scripts/launch_selenekto.py`, so make a backup first if you have edited that script. No other existing files are replaced. You must already have the terrain viewer milestone installed, and the horizon JSON files present. Your existing `.venv` has `rasterio` / `pyproj` from `[geo]`.

Run (PowerShell from outer infrastructure directory):
```
Test-Path .\src\selenekto_data\solar.py
Test-Path .\scripts\launch_selenekto.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_selenekto.py
```
Click **Calculate dated Sun timeline**. Requires network access to JPL; if Horizons is unavailable, the original viewer still works. For dates, start with `2026-11-14`, 72h, 60 minutes (73 samples).

## Scientific caveats
- JPL Horizons azimuth is referenced to local north, while NASA PGDA horizon azimuth is relative to projected `+Y`. We rotate the direction using the local projection derivative, but the complete **MOON_ME ↔ Horizons lunar frame** consistency remains **unverified**. Treat alignment as a prototype until independently cross-checked.
- We use the Site01 representative latitude −89.4632° and east longitude −137.49°, and 1944.63m DEM elevation as a **provisional spherical Moon surface height** for Horizons. Vertical datums may not exactly match.
- The horizon used a 5km local DEM search, 10m nearest-cell sampling, observer height 0m, not a physically surveyed instrument location. It misses distant obstruction and interpolation effects.
- Elevation ±1 RMS perturbation scenarios are **neither statistical confidence intervals nor guaranteed bounds**; the plotted band is not a probability of illumination.
- Sun results are **sampled estimates**: no interval interpolation, solar disk fraction, penumbra, self-shadowing, or precise duty cycle is calculated. No mission-grade sunlight or landing-safety claims.
- JPL Horizons availability, rate limits, and format can change. Parser deliberately fails rather than displaying ambiguous data.

JPL reference: https://ssd-api.jpl.nasa.gov/doc/horizons.html
