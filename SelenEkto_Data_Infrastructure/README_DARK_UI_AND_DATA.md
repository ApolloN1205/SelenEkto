# SelenEkto — Dark UI + NASA Region Data Health

## This package is an add-on, not a replacement

**Requirements:** the previous SelenEkto Unified Dashboard / 27 Regions add-on must already be installed. It provides `src/selenekto_data/unified_regions.py`, its NASA downloader, and candidate analysis scripts. The current ZIP does **not** contain NASA raster data.

Changes:
- A new launcher (`scripts/launch_selenekto_dark.py`) leaves `launch_unified_dashboard.py` intact.
- Every notebook tab and selected-tab label is dark with high-contrast text.
- Region and layer selectors use dark readonly dropdowns; candidate naming/renaming prompts have dark backgrounds.
- Tables and input fields are dark with readable selected rows.
- Adds a `DATA HEALTH` tab with a live per-region scan for missing rasters, invalid/misaligned GeoTIFFs and an approximate sparse-sample NoData overview.
- New standalone `scripts/audit_pgda_regions.py` outputs detailed local inventories to `data/processed/data_audit/region_audit.csv` and `.json`.
- When a clicked pixel lacks valid values, it explicitly reports `NoData`, which must not be read as elevation/slope zero.
- Existing NASA raster files and the old dashboard are untouched.

## Windows PowerShell — run from `SelenEkto_Data_Infrastructure`

1. Download the ZIP and use a Windows file picker to choose its *actual* location:

```powershell
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.OpenFileDialog
$picker.Title = 'Select SelenEkto Dark UI ZIP'
$picker.Filter = 'ZIP files (*.zip)|*.zip'
if ($picker.ShowDialog() -eq 'OK') {
    Expand-Archive -LiteralPath $picker.FileName -DestinationPath . -Force
    Write-Host 'Extracted:' $picker.FileName
}
```

2. Verify required files:

```powershell
Test-Path .\scripts\launch_selenekto_dark.py
Test-Path .\scripts\audit_pgda_regions.py
Test-Path .\src\selenekto_data\region_audit.py
Test-Path .\src\selenekto_data\unified_regions.py
```

All four must be True before proceeding.

3. Run tests and the read-only audit:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\audit_pgda_regions.py
```

4. Launch new dashboard:

```powershell
.\.venv\Scripts\python.exe .\scripts\launch_selenekto_dark.py
```

5. See `DATA HEALTH` tab and full CSV:

```powershell
explorer.exe .\data\processed\data_audit
```

6. If some regions show `incomplete`, try the existing **non-destructive** downloader to retrieve missing layers:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_all_pgda_regions.py --all
```

It skips files it can read; it does not repair an invalid existing file automatically. Some URLs in the broader NASA catalogue may not resolve. Keep the audit logs so failures can be investigated individually rather than misreported as downloaded data.

## Scientific notes

A region marked `ready` has five readable, mutually co-registered rasters with some valid values in the sparse overview sample; this is NOT validation of full terrain coverage. `sample_has_no_data` means a 128x128 overview of at least one layer was entirely invalid. Sampling can miss smaller NoData holes. A NoData cell must not be treated as a valid zero or included in a confident landing-site score. The current model remains a local DEM-limited experimental prototype, not a flight-validated illumination or landing safety product.

## Troubleshooting

If the new launcher is missing, do not run it: first confirm `Test-Path` and that the ZIP extracted directly into the project root. The Tkinter dark UI needs Windows theme support; OS-native error message boxes may still follow Windows light mode. If tests pass but a particular region is unavailable, inspect the CSV audit.
