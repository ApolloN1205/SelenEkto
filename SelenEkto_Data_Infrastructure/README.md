# SelenEkto — Explainable Candidate Comparison

This patch adds a working **Adjust comparison priorities** button to the existing PySide6 **Compare** tab. It patches the current installed launcher *in place*, makes a dated backup, and preserves your existing Settings, Aurora LOLA/Crimson colours, logo, and solar calculation fixes. It does not alter saved candidates, NASA data or prior scientific results.

## What it does

Select two or more saved candidates (Ctrl+click) in Compare, then select **Adjust comparison priorities**. The window offers weights 0–10 for:
- Gentler slope (low is preferred)
- Lower elevation RMS uncertainty (low is preferred)
- Lower slope RMS uncertainty (low is preferred)
- More directly observed LOLA spots at the selected pixel (high is preferred)

By default, it **does not declare a winner**. An optional checkbox highlights the highest *relative preference score* among the selected candidates. The score is normalized only over those candidates; it is not a probability of safety or landing suitability. If any weighted measurement is missing, that candidate is **unscored** with an explicit reason. A criterion with weight zero is ignored. Identical metric values contribute equally to the compared candidates. No values are fabricated. This version deliberately does not include solar exposure in the preference index because validated independent candidate-solar results are not universally available yet.

## Install in the existing infrastructure directory (PowerShell)

1. Download the ZIP and select it from a Windows file picker (see chat response).
2. Verify the new files exist:
   `Test-Path .\scripts\patch_selenekto_recommendations.py`
   `Test-Path .\src\selenekto_v2\recommendations.py`
3. Apply once (makes a timestamped backup of your active launcher):
   `.\.venv\Scripts\python.exe .\scripts\patch_selenekto_recommendations.py`
4. Run the six focused tests:
   `.\.venv\Scripts\python.exe -m pytest tests\test_recommendations.py -q`
5. Run the full tests:
   `.\.venv\Scripts\python.exe -m pytest tests -q`
6. Open the main app:
   `.\.venv\Scripts\python.exe .\scripts\launch_selenekto_v2_controls.py`

## Data prerequisites

To compare actual terrain measurements, your region's five source NASA rasters must be present and complete. After the existing download finishes, use the previously installed bulk downloader's verification command (check `--help` for available flags), regenerate real region profiles and refresh saved pixel data in Compare. Run this upgrade whether or not all regions have finished downloading: incomplete candidates will simply have clearly marked missing scores.

## Scope and quality

Six unit tests run successfully in the build environment. The patcher was tested on the known Settings-launcher version, including idempotent second-run behaviour. The complete, user-modified Windows app still needs local validation. This is not a full scientific validation or final executable.
