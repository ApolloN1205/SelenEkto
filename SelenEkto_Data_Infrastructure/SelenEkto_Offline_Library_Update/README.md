# SelenEkto — Offline Data Library milestone

A small, real feature update for the current PySide6 launcher.

## What it actually adds

- **Data Library** navigation page listing 27 known regions, even if no full NASA data is installed.
- Lightweight grayscale PNG previews generated **locally from original NASA elevation TIFFs**. These are downsampled visual references, not a source for pixel-level measurements.
- **Download selected region** button running the existing NASA downloader on a worker thread, using official NASA PGDA URLs. Five original TIFFs, potentially hundreds of MB; they are not bundled in the lightweight executable.
- Known warnings on LM8, Site20 and Site23. No invented data or misalignment assurances.
- Build patch bundles `data/catalog/previews` in portable distribution and **never** bundles full NASA TIFFs.
- Five unit tests for catalogue functionality.

## IMPORTANT: what it does NOT promise

- New user without any local source TIFFs will see the regional catalogue; a preview will only appear if you generated and bundled that region's PNG before packaging. There is no fabricated map.
- The existing Explorer continues to require original TIFFs for live per-pixel navigation.
- Download completion is not scientific validation. Run Data Health and verify alignment before calculations.
- The installer assumes a current launcher structurally compatible with the SelenEkto 2.0 Settings launcher. It refuses altered code rather than forcibly overwrite.
- Creating or using Windows developer-only junctions is **not** a public distribution solution. Never distribute a junction or private paths.

## Install (from SelenEkto_Data_Infrastructure)

1. Extract package into current infrastructure folder.
2. ` .\.venv\Scripts\python.exe .\scripts\install_offline_library.py `
3. ` .\.venv\Scripts\python.exe .\scripts\generate_offline_previews.py `
4. ` .\.venv\Scripts\python.exe -m pytest tests -q `
5. ` .\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2_controls.py `
6. Close app; rename old `dist\SelenEkto` to dated backup; then ` .\.venv\Scripts\python.exe .\scripts\build_windows_release.py `
7. Open fresh exe and check **Data Library** tab, previews, region download dialog.

If there is no `scripts/download_pgda_real.py` on your Windows project, copy the previously provided corrected downloader into scripts before trying an in-app download.
