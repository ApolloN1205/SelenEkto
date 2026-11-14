# SelenEkto — Local desktop milestone (14 Nov 2026)

This ZIP **adds** a real runnable Tkinter interface to the existing Python infrastructure: it does not replace your NASA datasets, prior modules or scripts. This is a first application milestone, **not yet the complete multi-site finished app**.

## Run (PowerShell, from SelenEkto_Data_Infrastructure)

```powershell
Expand-Archive "$HOME\Downloads\SelenEkto_Desktop_Milestone.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_selenekto.py
```

Install the package in editable mode first if your venv does not recognise `selenekto_data` in pytest:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[test,geo]"
```

Requires the existing `Site01_horizon_5km.json`; automatically loads `Site01_horizon_uncertainty_5km.json` if present. The Python installation must include Tkinter (typical Python on Windows) and Matplotlib. No actual elevation raster is loaded by the UI—it reads the reports already generated from your real data.

## What the app does

- Interactive monochrome horizon plot for Site01 with the deterministic low/high scenario band.
- Manually input a projected-grid direction and hypothetical sky altitude and see if the point is above/below the DEM-limited horizon scenarios.
- Import a CSV file with `timestamp_utc,grid_azimuth_deg,altitude_deg`, evaluate each position, and export a new CSV in the same folder with corresponding modelled obstruction results.
- This may be used with ephemeris from an **external** source, **only after** it is correctly expressed in the projected grid's azimuth convention. Lunar true north azimuth is not interchangeable with projected grid azimuth.

## Important limitations

- **Not a solar ephemeris:** entering a date or importing timestamped CSV rows does not calculate where the Sun is on the Moon.
- No illumination fraction, solar visibility guarantee, lunar landing safety, or mission-grade analysis is claimed.
- DEM is only one region; horizon algorithm has spatial/datum limitations described in its report. Perturbations using reported elevation RMS are deterministic scenarios, not confidence intervals.
- To become a real solar navigator, add a validated Sun-in-Moon-body-fixed coordinate calculation and the conversion to the projected-grid direction at each site. Then time-series evaluation can operate on those verified inputs.

## Expected CSV example (ILLUSTRATIVE / NOT ACTUAL SUN POSITION)

```csv
timestamp_utc,grid_azimuth_deg,altitude_deg
2026-11-14T00:00:00Z,10,2
2026-11-14T01:00:00Z,40,1
```

## Team handoff

Run all tests, open the application, take a screenshot for your progress log and commit the new `scripts/`, `src/`, `tests/` source files. Never commit the 200MB NASA TIFFs or `.venv`.
