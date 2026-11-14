# SelenEkto — Candidate map selection fix and horizon shortcut

## What changed
- Keeps the existing Site01 NASA map layers, candidate comparison, CSV export, and terrain/solar viewer shortcut.
- Moves the candidate buttons, status indicator, and candidate table ABOVE the large Matplotlib image, ensuring they remain visible on typical Windows displays.
- Adds immediately visible `SAVED Candidate XX` feedback, highlights the new table row and shows a clear error on duplicate clicks.
- Adds a dedicated `Analyze candidate horizons` button. When two or more map cells have been added, it automatically saves their CSV and launches the previously installed `scripts/analyze_candidate_horizons.py` in a separate console. Uses a 500 m local horizon, not site-wide illumination.
- Adds a small, testable `CandidateStore` class and four unit tests. The program does not auto-install other add-ons or download any NASA data.

## Installation
1. Close the current map application window (the solar viewer may stay open).
2. From the outer `SelenEkto_Data_Infrastructure` project folder, back up the current launcher:

   `Copy-Item .\scripts\launch_site_map.py .\scripts\launch_site_map_before_fix.py`

3. Download this ZIP and use a Windows file picker to locate it (do not assume it is in Downloads). Extract the **contents** into the outer `SelenEkto_Data_Infrastructure` root, merging `scripts`, `src`, `tests`.
4. Check:

   `Test-Path .\scripts\launch_site_map.py`
   `Test-Path .\src\selenekto_data\candidate_store.py`
   `Test-Path .\tests\test_candidate_store.py`

5. Run:

   `.\.venv\Scripts\python.exe -m pytest tests -q`
   `.\.venv\Scripts\python.exe .\scripts\launch_site_map.py`

## Verify behavior
- Click the image; a red plus and row/column details should appear.
- Click **Add selected cell** in the toolbar ABOVE the map.
- A table row must immediately appear, and the status line should say `SAVED Candidate 01`.
- Add a second DIFFERENT cell. Press **Compare candidates** to see terrain charts.
- Press **Analyze candidate horizons** to run the separate independent-horizons script. This requires `scripts/analyze_candidate_horizons.py` from the previous Candidate Horizons add-on. If absent, the app tells you so instead of silently doing nothing.
- Outputs will appear in `data/processed/candidate_horizons/Site01/` when the analysis finishes.

## Limitations
- Still only Site01. Other sites need their own real NASA data and per-site coordinate/horizon processing.
- Tests cover candidate selection logic; GUI behavior still requires verification on Windows.
- DEM-derived horizon estimates are local and cannot be called validated solar exposure or landing-site safety.
