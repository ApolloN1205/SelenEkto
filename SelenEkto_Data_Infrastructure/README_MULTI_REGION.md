# SelenEkto — Multi-region terrain explorer + named candidate sites

The existing four-tab dashboard and Site01 scripts are not replaced. This milestone provides an **additional** multi-region explorer which discovers only actual installed NASA PGDA LOLA_5mpp data. Six documented region IDs in this particular source collection are supported: Site01, Site04, Site07, Site11, Site20 and Site23. This is not a claim that these are the only lunar landing regions.

## Naming

Click a terrain cell → **Add candidate** → enter a custom name (e.g. `Ridge Alpha`). A candidate appears in the table with the name and region ID. Select a table row → **Rename selected** to change it. Renaming preserves pixel coordinates and all metrics. Export CSV retains the names and region IDs. Names are up to 64 characters, unique within a region. This is an app-level label, not an official NASA site name.

## Install

Extract the archive into your *existing* `SelenEkto_Data_Infrastructure` directory. Check with `Test-Path .\scripts\launch_multiregion.py`, then run ` .\.venv\Scripts\python.exe -m pytest tests -q` and `.\.venv\Scripts\python.exe .\scripts\launch_multiregion.py`.

To add a **real** NASA terrain region, run ` .\.venv\Scripts\python.exe .\scripts\download_lola_region.py --region Site04` from the infrastructure folder. This streams the five genuine NASA rasters (roughly 200MB combined depending on region), validates file georeferencing, and writes a manifest. Online access required. It does not overwrite installed files. Only attempt when you have space and a stable connection. Other supported values: Site07, Site11, Site20, Site23. Data source: https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/ .

**Scope:** Region switching, layer viewing, named point selection and CSV export only. The existing candidate horizon/solar scripts are still Site01-only; do not feed cross-region CSVs into them until multi-region calculation support is implemented and validated. No landing-safety claims.
