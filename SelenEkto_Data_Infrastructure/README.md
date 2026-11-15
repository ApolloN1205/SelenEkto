# SelenEkto — Developer guide

This directory contains the Python source, PySide6 desktop app, scientific utilities, datasets metadata, tests and Windows release tooling.

## Source layout

| Location | Purpose |
| --- | --- |
| `src/selenekto_data/` | Lunar raster loading, geodesy, horizon, JPL solar and data-processing code |
| `src/selenekto_v2/` | Desktop UI, offline library, preferences and candidate comparisons |
| `scripts/launch_selenekto_v2_controls.py` | Current development launcher |
| `scripts/download_pgda_real.py` | Selective NASA PGDA raster acquisition |
| `scripts/generate_offline_previews.py` | Generate slope PNG previews from installed rasters |
| `tests/` | Automated regression tests |
| `data/catalog/` | Lightweight region catalogue, profiles and preview images |
| `release/selenekto_entry.py` | PyInstaller Windows bootstrap |

Historical launchers and backup scripts remain in the repository for now; the current launcher is `launch_selenekto_v2_controls.py`. Avoid treating old scripts as the production entrypoint.

## Development on Windows

Use a compatible Python version and install the project's scientific/UI dependencies in a virtual environment. The `pyproject.toml` optional `geo` and `test` sets do **not** by themselves install the complete desktop app stack.

A typical development environment needs `PySide6`, `matplotlib`, `numpy`, `rasterio`, `pyproj`, `Pillow` and `pytest`; build tooling additionally needs `pyinstaller`. Review imports and dependency compatibility before choosing a Python release.

From this directory, with a configured environment:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2_controls.py
```

## Windows release

```powershell
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py prepare
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py audit
```

Only use the publish command and its manual-check flags **after** you have verified a clean extracted ZIP on a separate Windows environment, its slope previews, the missing-data explanations, and the selective downloader. See [release checklist](../docs/RELEASE_CHECKLIST.md).

Do **not** distribute a locally linked `data/raw/lola` junction. Keep the original high-resolution NASA TIFFs out of the portable download.

## Scientific limitations

- A preview is not sufficient to compute a new candidate's full terrain horizon.
- The candidate horizon is limited to the selected DEM and configured scan radius.
- Coordinate-frame assumptions and JPL observer geometry require independent cross-checks.
- Site20, Site23 and LM8 are excluded from usable datasets pending repair/validation.
- Do not interpret preference scores as landing safety.

## Documentation

- [Project overview](../README.md)
- [Dataset provenance](DATA_SOURCE_AUDIT.md)
- [Release checklist and known issues](../docs/RELEASE_CHECKLIST.md)
- [Original design dossier](../SELENEKTO_MASTER_PROJECT_DOSSIER.md)
