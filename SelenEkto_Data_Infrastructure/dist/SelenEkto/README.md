# SelenEkto — Final Consolidation

This patch is additive, idempotent, and does not delete NASA GeoTIFFs, profiles, or saved candidates.

- Excludes **LM8**, **Site20**, **Site23** from the **Data Library**, **Explorer region selector**, **Data Health table**, and **region-wide comparison**. Their underlying files are untouched; candidates already saved from them are also retained.
- Restores the **Obsidian** theme to near-black (`#06070A`), while retaining Graphite and all accent colours.
- Removes excluded region preview/profile copies from a **new portable build only**, without touching the development files.
- Does **not** claim scientific validation or a successful Windows clean-install test.

Extract ZIP into the `SelenEkto_Data_Infrastructure` folder. Close the executable first. Run:

```powershell
.\.venv\Scripts\python.exe .\scripts\apply_final_consolidation.py
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe .\scripts\generate_offline_previews.py
```

In SelenEkto **Settings**, choose **Obsidian**, then save. Existing preference files are not overwritten.

To rebuild, first rename `dist\SelenEkto` to a dated backup. Execute `scripts\build_windows_release.py`, then `scripts\check_portable_release.py` before publishing. **Do not run `local_release_link.py` on the distributable copy.** A successful check does not substitute for a clean-computer smoke test.

The public release still requires checking download functionality, independent startup, scientific uncertainty and the repository inventory. Keep a backup and do not delete historical project files until audited.
