# SelenEkto — Final Windows release gate (15 November 2026)

This is a **release-preparation tool**, not a replacement for your working SelenEkto code. It protects the project data, builds from your latest source and stages a distributable Windows folder without any locally linked NASA GeoTIFFs.

## What was verified here

The release builder, desktop bootstrap, Data Library/downloader, slope-preview generator and final catalogue/theme patches from previous packages were inspected. Eight automated tests of the **new release tools** passed in an isolated Linux environment, including synthetic raster alignment and ZIP-integrity tests. Your latest Windows repository, local NASA data, built EXE and hardware **are not accessible here**: they cannot be independently certified remotely. The program correctly refuses to publish before you explicitly attest to GUI and download tests.

## 1. Install the small ZIP

Close SelenEkto. Extract the ZIP into `SelenEkto_Data_Infrastructure` (not into a second `SelenEkto_Final_Release_Gate` folder). It should install:

- `scripts/final_release_gate.py`
- `scripts/validate_raster_alignment.py`
- `tests/test_final_release_gate.py` and `tests/test_raster_screen.py`
- `FINAL_RELEASE_GUIDE.md`

The patch does **not** delete your data or replace the launcher.

## 2. Run the complete preparation gate

In PowerShell, within `SelenEkto_Data_Infrastructure`:

```powershell
$ErrorActionPreference = 'Stop'
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py prepare
if ($LASTEXITCODE -ne 0) { throw 'SelenEkto release preparation failed. Do not ZIP.' }
```

What it does:

1. Compiles the source and scripts.
2. Runs your **complete** `pytest tests -q` suite, including the new regression tests.
3. Regenerates genuine NASA slope previews where slope rasters exist.
4. Checks metadata, raster-grid alignment and sampled slope values for the **24 included regions**. Saves a report to `data/processed/release/raster_alignment_screen.json`. Any scientific problems must be investigated. This is a screening test, **not independent astronomical validation**.
5. Makes a backed-up, minimal change to the Windows builder so dynamically loaded `urllib.request` works and the generated manifest no longer includes a personal source path.
6. Moves the old `dist/SelenEkto` aside without deleting it, builds a fresh PyInstaller executable and creates a **detached distribution stage** at `release_ready/staging_.../SelenEkto`.
7. Removes the developer-only repair scripts, backups, raw-data links, saved candidates and saved preferences from the staged folder. Keeps PyInstaller's `_internal` directory, app modules, slope previews and the on-demand NASA downloader.
8. Performs strict static checks. Any failure **blocks publication**.

If preparation stops because of a failing test, missing preview, leaked local path or dependency error, **do not ZIP**. Use the exact printed problem to repair that issue, then rerun the command. Never remove a check merely to make a ZIP.

## 3. Verify the *detached* application manually

```powershell
$stage = (Get-Content .\release_ready\latest_stage.txt -Raw).Trim()
Start-Process (Join-Path $stage 'SelenEkto.exe')
```

Check the following in the staged application, not in `dist`:

- It opens by double-clicking `SelenEkto.exe`, without separately running Python or PowerShell.
- The sidebar loads; the logo is used only for the **Windows executable/window/taskbar icon**, not as a large image inside the sidebar.
- Settings → **Obsidian** restores the very dark `#06070A` look, and **Slope** is the default terrain layer. Aurora LOLA and Crimson remain choices.
- Data Library shows genuine **slope** previews; LM8, Site20 and Site23 are absent. There are no newly bundled TIFFs.
- Before a download, Explorer clearly explains when no full-resolution dataset is installed. This should not be a mysterious blank/black map.
- Test **Download selected region** for one of the 24 supported regions. Check that the five NASA files are saved into **that staged folder's** `data/raw/lola/<region>`, the app does not try to invoke `python.exe`, and the result can be refreshed. Downloads may be hundreds of MB; use one region only. If downloading is unavailable or fails, don't claim this works.
- Check Compare and Illumination on a region with validated data; no missing metric is fabricated. Scores remain comparative, **not** real landing-safety probabilities.
- Exit and reopen. Verify Settings persists.

Because the downloader writes to the staged folder, after testing you may have full-resolution TIFFs in that folder. **Do not ZIP the folder you just downloaded into.** The audit will block it. Instead perform the download test in a temporary copy of the stage:

```powershell
$stage = (Get-Content .\release_ready\latest_stage.txt -Raw).Trim()
$test = Join-Path $env:TEMP ('SelenEkto_Download_Test_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
robocopy $stage $test /E /XJ /R:1 /W:1 | Out-Null
if ($LASTEXITCODE -ge 8) { throw 'Clean test copy failed.' }
Start-Process (Join-Path $test 'SelenEkto.exe')
```

Use the **temporary copy** for the download test. Leave your clean staged folder untouched. A successful test on the same machine still isn't proof of performance on a different Windows computer with no Python installed; verify on a separate machine or Windows VM before a broad public release.

## 4. Re-audit and create ZIP + SHA256

Only after you **personally confirmed** all of those checks:

```powershell
.\.venv\Scripts\python.exe .\scripts\final_release_gate.py audit
if ($LASTEXITCODE -ne 0) { throw 'Final release audit failed.' }

.\.venv\Scripts\python.exe .\scripts\final_release_gate.py publish --confirm-smoke --confirm-downloader
if ($LASTEXITCODE -ne 0) { throw 'Release ZIP was blocked.' }

Get-ChildItem .\release_ready -Filter 'SelenEkto_Windows_Research_Preview_*.zip' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1 Name, @{Name='MB';Expression={[math]::Round($_.Length/1MB,1)}}
```

The package will be named `SelenEkto_Windows_Research_Preview_<UTC>.zip` and a `.zip.sha256` checksum will accompany it. The script re-audits **immediately before packaging** and verifies the ZIP's internal integrity. The words `--confirm-smoke` and `--confirm-downloader` are your attestations, not automated tests.

## 5. Git / privacy housekeeping

Before sharing the source repository, run:

```powershell
git status --short
git diff --check
git ls-files | Select-String '\.(tif|tiff|part|exe|pyd|dll)$|(^|/)(\.venv|dist|build|release_ready|_archive)/'
```

If that final command lists tracked raw TIFFs, secrets or build outputs, investigate before publishing. `.gitignore` doesn't untrack already tracked files. Do **not** delete the original files from disk or use `git clean -fdx` as a shortcut. Ensure `.gitignore` covers `data/raw/lola/`, `.venv/`, `dist/`, `build/`, `release_ready/`, `_archive/`, `__pycache__/`, `.pytest_cache/` and local logs/settings where appropriate. Preserve science source references and citations in documentation.

## Honest scientific release status

The supplied alignment screen validates file presence, raster dimensions/transforms/CRS and small representative samples. It **does not** independently establish Moon coordinate-frame correctness, horizon accuracy, spacecraft illumination or landing safety. Keep the app labelled **research preview**, visibly describe uncertainty and use NASA PGDA/LOLA attribution. Only call it fully validated after reference comparisons with authoritative geodesy/ephemeris cases and user testing on another PC.

The downloadable SelenEkto ZIP should include **app + compact slope previews + on-demand downloader**, **not** the original gigabytes of TIFFs. ZIP size is printed automatically. This package will be significantly smaller than bundling every dataset, but actual compressed size depends on the PySide6/GDAL/Rasterio libraries built on your Windows PC.
