# SelenEkto — Independent candidate horizon profiles

This is a **separate additional tool**, not a replacement for the working site map or solar viewer. It reads the actual CSV exported from the interactive map and computes a NEW terrain horizon for EVERY selected cell. Results are not transferred from Connecting Ridge's centre point.

## Installation

1. Download SelenEkto_Candidate_Horizons.zip.
2. In PowerShell at your OUTER `SelenEkto_Data_Infrastructure` directory, select the actual downloaded ZIP using the file picker:

```powershell
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.OpenFileDialog
$picker.Filter = 'ZIP files (*.zip)|*.zip'
if ($picker.ShowDialog() -eq 'OK') { Expand-Archive -LiteralPath $picker.FileName -DestinationPath . -Force }
```

3. Verify, test and launch:

```powershell
Test-Path .\scripts\analyze_candidate_horizons.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_site_map.py
```

4. On the map: click two or three distinct cells, **Add selected cell**, **Export candidate CSV**. Close map if convenient.
5. Analyse them by choosing the just-exported CSV when the file picker opens:

```powershell
.\.venv\Scripts\python.exe .\scripts\analyze_candidate_horizons.py
```

6. Open the resulting files:

```powershell
explorer.exe .\data\processed\candidate_horizons\Site01
```

Option: `--max-distance-m 2000` to scan 2 km rather than the default 500 m. The map only covers Site01. For other regions separate data will be needed.

## Technical cautions

- AZIMUTHS ARE GRID-RELATIVE, clockwise from projected +Y. This is not geographic north.
- Each chosen pixel has an independent observer position at the cell centre, with observer height 0 m.
- Angles are from terrain DEM only, sampling every 10 m. Samples can be missing or clipped at the raster edge; see the JSON.
- Elevation errors and interpolated LOLA coverage remain relevant. This add-on does not propagate full uncertainty per candidate.
- A per-candidate terrain horizon is **not** dated solar visibility or landing-safety certification.
