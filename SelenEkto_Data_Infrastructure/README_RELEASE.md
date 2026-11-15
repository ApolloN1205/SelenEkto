# SelenEkto — Release-readiness milestone

This package is **not** the finished Windows executable. It is a tested, **non-destructive** preflight and a repeatable Windows build recipe for your current PySide6 application. Build and test the executable on Windows.

## What is included

- `scripts/release_preflight.py`: checks main launcher, installed Python libraries, region TIFF presence, and compact JSON profiles; writes a JSON report only if `--save` is supplied. **Does not claim the TIFFs are scientifically valid.**
- `scripts/create_windows_icon.py`: uses `assets/branding/logo.png` to create `logo.ico` for Windows taskbar/exe branding.
- `scripts/build_windows_release.py`: generates a portable `dist/SelenEkto/` folder using PyInstaller on Windows. It intentionally excludes full-resolution NASA TIFFs; copies source files and compact catalogue JSON to match the existing application's filesystem assumptions. It refuses to overwrite an existing release folder.
- `release/selenekto_entry.py`: no-console launcher with a startup traceback log in `data/processed/logs/release_startup_error.log`.
- `tests/test_release_preflight.py`: four tests for preflight, including avoiding false claims about corrupted TIFFs.

## Install

Extract the ZIP **into the outer** `SelenEkto_Data_Infrastructure` directory. Before extraction verify the selected ZIP is the release readiness package, not an unrelated download.

```powershell
# These assume you are already inside SelenEkto_Data_Infrastructure.
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.OpenFileDialog
$picker.Filter = 'ZIP files (*.zip)|*.zip'
if ($picker.ShowDialog() -eq 'OK') {
    Expand-Archive -LiteralPath $picker.FileName -DestinationPath . -Force
    Write-Host "Extracted $($picker.FileName)"
}
Test-Path .\scripts\release_preflight.py
Test-Path .\scripts\build_windows_release.py
```

## Check your current state

```powershell
.\.venv\Scripts\python.exe .\scripts\release_preflight.py --save
.\.venv\Scripts\python.exe -m pytest tests -q
```

**LM8** was reported incomplete, while **Site20** and **Site23** were reported invalid/misaligned. File presence is not proof of raster validity. Keep these regions in the catalogue with explanatory labels; do not invent measurements or silently delete them.

## Prepare Windows branding

Place your logo in `assets/branding/logo.png` and execute:

```powershell
.\.venv\Scripts\python.exe .\scripts\create_windows_icon.py
```

## Build the portable Windows application

Only after the main application passes its end-to-end tests:

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller pillow
.\.venv\Scripts\python.exe .\scripts\build_windows_release.py --dry-run
.\.venv\Scripts\python.exe .\scripts\build_windows_release.py
```

Then open `dist/SelenEkto/SelenEkto.exe`. The app uses the same folder for user files and logs; distribute it as a **writable, unzipped** portable folder. Don't place it in `C:\Program Files` for this first build. If you have already built once, move `dist/SelenEkto` elsewhere before rebuilding; the script refuses to overwrite it.

Test the *built* executable, not only the Python launcher, on a clean Windows machine. Verify icon, startup, candidate save/reload, Compare, Illumination, and error messages. If it exits without showing a window, read `dist/SelenEkto/data/processed/logs/release_startup_error.log`. Packaging dependencies may need adjustment for your local installed versions, particularly with Python 3.15.

## Keep release small

- `dist/SelenEkto` includes code and processed region-profile JSON, **not** `data/raw/lola` TIFF rasters. Its exact size can be measured only after a Windows build.
- Viewer/whole-region comparisons can use processed profiles. New pixel sampling, horizons and advanced analyses still need the real corresponding NASA TIFFs.
- Offer the TIFFs separately as an optional, provenance-verified dataset download. Never represent profile summaries as a substitute for 5 m/pixel data.

## GitHub

Commit source, unit tests, `.gitignore`, reproducible download instructions, small catalogues, and provenance. Review `git status` and staged files before committing; exclude `.venv`, `dist/`, `build/`, raw raster binaries and logs. If any large TIFF was already tracked, `.gitignore` alone will not untrack it. Avoid destructive cleanup without checking what is staged.

## Finish-line checklist

1. Real slope/elevation/LOLA statistics for every truly usable region; LM8, Site20, Site23 appropriately flagged until fixed.
2. Separate raster-based measurements for selected candidate pixels; compare data only where available.
3. Candidate-specific horizon and solar results checked for several regions; horizon/solar reference frame alignment independently reviewed.
4. Recommendation engine tested with missing-data cases, and scoring explicitly distinguished from landing safety.
5. Branding and settings persist; runnable app logs actionable error messages.
6. Portable executable tested on Windows. Source code and dataset reproduction instructions committed.

No GeoTIFF or user project was modified to prepare this package.
