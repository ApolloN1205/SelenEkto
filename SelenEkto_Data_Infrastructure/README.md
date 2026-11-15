# SelenEkto — release profile privacy repair

The static audit identified absolute Windows user paths in 24 terrain-profile JSON files and in `local_raster_inventory.json`. The staged directory is otherwise 304.9 MiB and has 24 slope previews.

This patch fixes the **already-created staging directory** rather than rebuilding the executable. It converts private absolute paths inside terrain profiles to portable `data/...` references when they have an unambiguous recognized anchor. The local raster inventory is excluded from the *staged copy only*. It does **not** alter the source profiles, your original NASA rasters or the calculations. Originals from the modified staged files are backed up under `release_ready/privacy_backups_.../`, **outside** the distributable folder.

If a private path can't be safely converted, it refuses to proceed; it will not silently alter a scientific field or manufacture a path. The existing full release audit runs again and must pass before `latest_stage.txt` is created. A small hook is installed so future `prepare` builds apply the same privacy correction before their audit.

## Install and repair

Extract `SelenEkto_Release_Privacy_Fix.zip` into `SelenEkto_Data_Infrastructure` (ZIP root contains `scripts/` and `tests/`).

```powershell
.\.venv\Scripts\python.exe .\scripts\fix_release_profile_privacy.py
```

Then:

```powershell
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py audit
$stage = (Get-Content .\release_ready\latest_stage.txt -Raw).Trim()
Start-Process -FilePath (Join-Path $stage 'SelenEkto.exe')
```

Check the staged application, without a local data junction: launch without Python, 24 offline slope previews, warnings when raw rasters are missing, clear statuses, excluded regions, and a successful single-region NASA download using the app itself. Only after these real checks:

```powershell
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py publish --confirm-smoke --confirm-downloader
```

Don't use these flags unless the corresponding manual tests passed. A ZIP/checksum will appear in `release_ready/`. The separate independent solar/coordinate scientific validation remains outstanding; distribute only as a **research/educational preview**.
