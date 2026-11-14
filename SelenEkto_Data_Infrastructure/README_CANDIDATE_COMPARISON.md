# SelenEkto — Candidate Comparison Add-on

This upgrades the **existing Site01 terrain map**, not the terrain+solar viewer. It replaces only `scripts/launch_site_map.py` and adds a pure analysis helper and three tests. It does NOT download additional NASA rasters.

## Install
Download the ZIP; choose it explicitly in the Windows picker if unsure where it was saved. From the **outer** SelenEkto_Data_Infrastructure folder in PowerShell:

```powershell
Copy-Item .\scripts\launch_site_map.py .\scripts\launch_site_map_before_comparison.py
Add-Type -AssemblyName System.Windows.Forms
$picker = New-Object System.Windows.Forms.OpenFileDialog
$picker.Filter = 'ZIP files (*.zip)|*.zip'
if ($picker.ShowDialog() -eq 'OK') { Expand-Archive -LiteralPath $picker.FileName -DestinationPath . -Force }
Test-Path .\src\selenekto_data\candidate_compare.py
Test-Path .\tests\test_candidate_compare.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_site_map.py
```

## Use
1. Click **on the plotted image**; the selected cell's measurements appear in the header.
2. Click **Add selected cell** at the bottom. It appears in the table; repeat for at least two candidate cells.
3. Click **Compare candidates** to see four side-by-side attribute charts in a new window.
4. Export your candidate CSV if desired. This is a display and exploratory comparison only.

## Scientific limits
- All clicked candidates are within the NASA Site01 raster, **not independent landing sites**; no safety score is calculated.
- Only the existing Site01 reference point has a computed horizon and solar timeline. Those results **cannot** be assigned to other clicked cells.
- Missing raster measurements remain missing, not zero. LOLA spot count 0 signifies a raster cell without a directly recorded spot and may reflect interpolation.
