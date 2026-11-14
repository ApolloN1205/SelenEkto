# SelenEkto — Repaired integrated dashboard

This is a **repair release**, not another loosely-connected new viewer. It does not overwrite previously working launcher scripts. The new launcher is `scripts/launch_selenekto_repaired.py`.

## Fixes

1. **NASA downloads:** Fixes the previous downloader's incorrect URL, which omitted the region directory. For instance Site04's real TIFF is hosted at `https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif`. The bulk downloader skips existing readable rasters; it never silently replaces corrupt files. Run audit to identify those separately.
2. **Explicit comparison choices:** Saved candidates are selectable as a multi-selection list in COMPARE. Ctrl+click adds candidates to the comparison. `Compare selected metrics` plots slope, elevation, elevation RMS, and LOLA counts only for the selected ones. NoData is labelled.
3. **Side-by-side image panels:** Select a left candidate and a right candidate in COMPARE and choose the NASA layer (elevation, slope, uncertainties, LOLA count). `Show side-by-side images` creates two 201x201 pixel cutouts around the saved cells, both at native 5m/pixel resolution, with the selected cells marked. Validity depends on the actual raster.
4. **Solar + horizon buttons:** Select two candidates in COMPARE; press `Calculate selected horizons` or `Calculate LIVE candidate Sun + horizon`. The separate worker writes `data/processed/unified/last_analysis.log` and the app checks its exit status. In case of failure the GUI shows the last error instead of silently claiming success.
5. **Data health:** The DATA HEALTH tab automatically audits every region and displays missing, invalid, grid-mismatched and sampled-NoData conditions. The Refresh and Export actions work. Audit is non-destructive.
6. **Dark UI:** Dark tabs, dropdowns, list selections, labels, controls, and candidate naming dialog. On some Windows Tk builds the native drop-down popup may still be affected by system theme; the selected field itself is dark.
7. **Candidate persistence:** Named candidates are automatically saved to `data/processed/unified/saved_named_candidates.csv` and reloaded when app starts. Previously exported CSVs are not automatically imported.

## Install

Close the previous dashboard. Save the ZIP anywhere and select it with the native picker:

```powershell
Add-Type -AssemblyName System.Windows.Forms
$p = New-Object System.Windows.Forms.OpenFileDialog
$p.Filter = 'ZIP files (*.zip)|*.zip'
if ($p.ShowDialog() -eq 'OK') { Expand-Archive -LiteralPath $p.FileName -DestinationPath . -Force }
```

From the `SelenEkto_Data_Infrastructure` directory:

```powershell
Test-Path .\scripts\launch_selenekto_repaired.py
Test-Path .\src\selenekto_data\repair_utils.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\launch_selenekto_repaired.py
```

The installed existing `region_audit.py`, `unified_regions.py`, `horizon.py`, `candidate_solar.py`, and `solar.py` modules are required. The earlier add-ons already supplied them. If imports fail, preserve the traceback, rather than rerunning the install blindly.

## Data health and corrected bulk downloads

For DATA HEALTH: open that tab and read the automatically populated 27-row table. Click Refresh to rerun. Use `Retry missing downloads (corrected URLs)` to launch the corrected downloader.

Or run the corrected downloader from PowerShell:

```powershell
.\.venv\Scripts\python.exe .\scripts\download_all_pgda_regions.py --all
```

**Do not overwrite corrupt or incomplete existing GeoTIFFs without checking them.** The downloader reports them and skips; manual review or renaming after a backup may be required. The Data Health sparse raster sample does **not** prove the entire raster contains valid pixels. Disk requirements may be several GB, and availability of remote files is subject to NASA service.

## Compare and solar walkthrough

1. Terrain Map → pick installed region, click image, Add named candidate; repeat for two or more locations. If the chosen cell has no elevation, choose another.
2. Compare → Ctrl+click two or more saved candidates, then `Compare selected metrics`. Choose left/right candidates and a layer, then `Show side-by-side images`.
3. Solar + Horizons → calculate selected horizons (offline) to validate analysis worker first; then calculate LIVE candidate Sun + horizon (requires internet/JPL Horizons). After successful live processing, `Load dated results` populates the table.
4. Worker results are under `data/processed/unified/YYYY-MM-DD/`; full log is `data/processed/unified/last_analysis.log`.

## Science limitations

These are local, finite-extent 5m DEM horizon calculations with preliminary lunar coordinate alignment and RMS terrain-error limitations. NASA PGDA reports high interpolation rates for these DEMs. JPL Sun centre above the modelled horizon at sample time is not validated landing safety. NoNoData pixels or lack of available raster data must not be interpreted as zero slope or zero obstruction.
