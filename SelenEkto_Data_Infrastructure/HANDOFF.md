# SelenEkto — Current project handoff (15 November 2026)

## User's confirmed state
- Windows 11 project: `C:\Users\Norbert\OneDrive\Documents\GitHub\SelenEkto\SelenEkto_Data_Infrastructure` (Git repo root is parent).
- PySide6 SelenEkto 2.0 is working. Features developed: Explorer, saved named candidates, visual comparison, JPL solar/horizon integration, Settings with accent colours, and adjustable preference comparison.
- Site01 originally had five usable NASA 5mpp raster TIFFs and verified terrain-profile output.
- Bulk download later attempted for 27 regions. User reports **LM8 incomplete**, **Site20 and Site23 invalid/misaligned**. Do not assert all 27 are usable or erase the problematic regions. State of other 24 regions requires verification locally.
- User wants display name **SelenEkto**, custom `assets/branding/logo.png`; accents Aurora LOLA pastel purple and Crimson red, neon yellow solar line.
- Fixed earlier QThread bug by using `self.start_utc` instead of shadowing `QThread.start`.
- Source launcher `scripts/launch_selenekto_v2_controls.py` after the Settings and Recommendation patches. This latest exact Windows file is not available in the assistant container; do not assume the downloaded patch is installed without verification.

## Release-readiness addition (this turn)
- Deliver `SelenEkto_Release_Readiness.zip` containing read-only preflight, portable Windows PyInstaller build script, console-free entrypoint, Windows icon generator, tests, and documentation.
- Package unit tests: four passing on Linux with synthetic directory fixtures. Actual Windows executable not built or verified here.
- `release_preflight.py --save` gives `data/processed/release/preflight.json` and reports missing TIFF layers without inventing data.
- PyInstaller build intentionally **excludes raw GeoTIFFs**; copies source, scripts, assets and compact region profiles to `dist/SelenEkto`. New arbitrary-pixel terrain analyses require optional NASA data downloaded separately.
- Build may require environment-specific PyInstaller dependency fixes. No packaging or exe success claimed until user runs it on Windows.

## Remaining priority work
1. Verify locally downloaded NASA rasters, repair LM8 or leave flagged incomplete; Site20 and Site23 remain flagged invalid/misaligned pending validation.
2. Verify candidate-specific numeric compare and solar/horizon with several non-Site01 regions. Ensure missing layers produce explanatory errors.
3. Independent scientific review of lunar coordinate transforms, reference frames, horizon distance and uncertainties.
4. Confirm recommendation workflow and user Settings/branding persist.
5. Execute Windows preflight, PyInstaller build, clean-machine smoke test; measure size; Git commit source/compact profiles only.
6. Prepare polished README, NASA dataset provenance and demonstration/submission artifacts.
