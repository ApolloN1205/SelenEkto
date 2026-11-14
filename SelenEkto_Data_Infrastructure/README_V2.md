# SelenEkto 2.0 — FIRST PySide6 FRONTEND

## What it is
An **independent launcher** for a black/dark, map-first lunar navigator. It leaves older SelenEkto scripts and data unchanged. This first release provides a full-resolution-cell map picker, named candidates persisted to JSON, explicit metric comparisons, side-by-side imagery, data-health status for installed regions, a reference horizon graph, and a button to open the existing working Site01 solar viewer.

**Not included yet:** independently validated solar/horizon calculations for every region. The older Site01 solar viewer is deliberately kept separate until the backend is generalized. Don't imply otherwise.

## Install — Windows PowerShell
Run from `SelenEkto_Data_Infrastructure`, **not** the parent `SelenEkto` folder.

1. Download `SelenEkto_2_0_PySide6.zip` and extract it **into that infrastructure directory** (the ZIP itself contains `src/`, `scripts/`, `tests/`). Use a ZIP selection dialog if unsure of the download path.
2. Check `Test-Path .\scripts\launch_selenekto_v2.py` returns `True`.
3. Install new dependency with ` .\.venv\Scripts\python.exe -m pip install PySide6 `.
4. Run ` .\.venv\Scripts\python.exe -m pytest tests -q `.
5. Launch ` .\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2.py `.

## Workflow
- **Explorer:** choose any READY region and layer. Click to inspect full-resolution data; save, rename and remove named candidates. The interface saves them in `data/catalog/named_candidates.json`, versionable after reviewing the names. Individual source NASA TIFF pixels remain local.
- **Compare:** Ctrl+click rows to choose candidates and click **Compare selected metrics**. Or select two candidates in dropdowns and click **Show image comparison** for spatially matched 241×241-pixel local windows (truncated near edges), at the original 5 m/pixel scale.
- **Illumination:** load your actual Site01 reference horizon; launch your existing solar viewer for live JPL calculations. Do not mistake the Site01 reference result for every candidate's solar result.
- **Data Health:** lists present region datasets, distinguishes missing, corrupt and misaligned. Use older download/conversion utilities for missing areas; this version does not automatically download large files.

## Limitations and operations
- Raster overviews are for UI display, cell measurements are read from original TIFFs on click.
- The selected location's slope can be absent or NoData. This is shown rather than assigned a fake value.
- Candidate observations and terrain comparisons are not landing-safety certifications.
- No comprehensive Windows GUI test was possible here. Seven core regression tests ran with synthetic rasters. A crash log is written to `data/processed/logs/selenekto_v2_crash.log` when uncaught exceptions occur.
- Old launchers and files are untouched; PySide6 is a new package, not a rewrite of the scientific code.
