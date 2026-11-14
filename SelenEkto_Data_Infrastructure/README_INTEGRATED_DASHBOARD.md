# SELENEKTO · Integrated desktop dashboard milestone

This is an **additive prototype** that does not overwrite the working original map or solar launcher. It installs:

- `scripts/launch_dashboard.py`: new Tkinter tabbed desktop navigator
- `src/selenekto_data/dashboard_data.py`: pure helpers for discovering installed regions and loading existing comparison reports
- `tests/test_dashboard_data.py`: five offline tests

## Install in the OUTER existing SelenEkto_Data_Infrastructure directory

1. Download the ZIP, select its real location in the Windows file picker below and extract with `-Force`.
2. Verify `Test-Path .\scripts\launch_dashboard.py` and `Test-Path .\src\selenekto_data\dashboard_data.py` both say True.
3. Run ` .\.venv\Scripts\python.exe -m pytest tests -q `.
4. Run ` .\.venv\Scripts\python.exe .\scripts\launch_dashboard.py `.

```powershell
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.OpenFileDialog
$picker.Title = 'Select SelenEkto Integrated Dashboard ZIP'
$picker.Filter = 'ZIP files (*.zip)|*.zip'
if ($picker.ShowDialog() -eq 'OK') {
    Expand-Archive -LiteralPath $picker.FileName -DestinationPath (Get-Location).Path -Force
    Write-Host 'Extracted:' $picker.FileName
}
Test-Path .\scripts\launch_dashboard.py
Test-Path .\src\selenekto_data\dashboard_data.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_dashboard.py
```

## Tabs

- **Overview** — actual installed dataset region discovery and links to previously working viewers.
- **Terrain Map** — new *embedded* real Site01 raster map; choose layer, click cells, add/remove candidates, export a CSV and launch independent candidate-horizon calculations. Candidate selection is in memory until you export or run the analysis; it does not change NASA source files.
- **Horizon** — existing Site01 reference horizon plot and access to existing viewer.
- **Solar & Candidates** — start the existing per-candidate JPL analysis with chosen dates and weights; refresh table from the latest successfully generated candidate solar JSON report. Computations run in a separate terminal and need to finish before refreshing the report.

## Prerequisites and limitations

- Existing packages `numpy`, `rasterio`, `matplotlib`, `pyproj` and your original modules.
- Existing `scripts/analyze_candidate_horizons.py` and `scripts/analyze_candidate_solar.py` are required for analysis buttons; the dashboard warns if missing.
- Only Site01's terrain imagery is embedded. Overview **discovers** installed compatible regions, but **does not** yet analyze or display them.
- The weights alter **new runs** of candidate solar comparison; they do not retroactively rescore already exported results.
- A Sun-centre above a local DEM horizon is not proof of continuous illumination, and **no outcome certifies landing suitability**.
- Dataset/reference-frame cross-verification and distant-ridge horizon coverage remain open scientific work.
- The dashboard was syntax-checked and its pure helpers unit-tested outside Windows; actual Tkinter GUI behavior must be verified locally.
