# SelenEkto — Persistent Settings Upgrade

Adds a working Settings page to the **existing PySide6 controls launcher**. It does not touch any NASA GeoTIFF, candidate data, or prior solar/horizon results.

## What can be changed?
- Dark theme: Obsidian or Graphite
- Accent colour: Neon yellow, Coral, or Ice blue
- Interface text size: 10–17 px
- Default Explorer map layer (five available layers)
- Default solar timeline duration and sample interval
- Confirmation prompt before deleting saved candidate locations
- Restore default settings

Preferences are stored at `data/config/desktop_settings.json`; this is a small file safe to version or ignore depending on personal preference.

## Install from infrastructure folder
1. Close SelenEkto. Select and extract this ZIP **into `SelenEkto_Data_Infrastructure`** (not its parent directory).
2. Verify `Test-Path .\scripts\launch_selenekto_v2_settings.py` returns `True`.
3. Backup your current launcher:
   `Copy-Item .\scripts\launch_selenekto_v2_controls.py .\scripts\launch_selenekto_v2_controls_pre_settings.py`
4. Replace the active launcher:
   `Copy-Item .\scripts\launch_selenekto_v2_settings.py .\scripts\launch_selenekto_v2_controls.py -Force`
5. Run:
   `.\.venv\Scripts\python.exe -m pytest tests\test_settings_store.py -q`
6. Launch as normal:
   `.\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2_controls.py`

This update includes the correction to the earlier QThread `self.start` / datetime naming collision.

## Behaviour and limitations
- 'Save and apply' writes preferences immediately and applies the colour/text styling; solar defaults and the preferred layer update in the current app.
- Theme changes colour controls; the underlying Matplotlib lunar raster and modelled solar series retain their scientific/visual colour mappings. The Sun remains neon yellow.
- The app needs your original installed `selenekto_v2` backend modules and dependencies; the ZIP is an upgrade, not a full standalone copy of SelenEkto.
- The stored file does not contain secrets or credentials.
- The five new preference-store tests passed locally. Qt GUI was not executed in the build environment; verify the screen and button interactions on Windows.
