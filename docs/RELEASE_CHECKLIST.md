# SelenEkto — Release checklist and open issues

SelenEkto is currently a **research / educational preview**, not scientifically validated mission-planning software.

## Distribution verification

- [x] The project has a published Windows pre-release asset at [V1.0](https://github.com/ApolloN1205/SelenEkto/releases/tag/V1.0).
- [x] A Windows portable build has been reported to launch on another computer.
- [ ] Test a **fresh download of the actual GitHub Release ZIP** in a new folder, with no locally linked NASA raster directory.
- [ ] Verify the packaged `_internal/base_library.zip` is readable and contains the Python `encodings` module (to prevent the previous Git LFS-pointer packaging regression).
- [ ] Compare SHA-256 hashes of the uploaded and downloaded ZIP files.
- [ ] Confirm all 24 offline **slope** previews load, missing-data messages are clear, and LM8/Site20/Site23 are excluded from selection.
- [ ] Confirm one supported region can be downloaded on demand and used for full-resolution analysis.
- [ ] Review release contents for local usernames, personal file paths, junctions and large GeoTIFFs.
- [ ] Validate Windows branding and Settings persistence on the clean install.

## Scientific / functional checks

- [x] The reference-site Python JPL Horizons request returned three Sun-position samples in a local development test (2026-11-15).
- [ ] **Unresolved: candidate-specific JPL Illumination feature** — reproduce the exact error in the current packaged executable; verify local raster data availability, candidate DEM-to-geographic coordinates, the Horizons response and the result plotting separately. A successful reference-site API request does not prove the whole workflow.
- [ ] Independently verify lunar south-pole coordinate transforms and Moon reference-frame alignment.
- [ ] Compare computed slope and DEM-derived terrain horizon outputs against trusted independent reference calculations.
- [ ] Verify uncertainty and partial-coverage warnings; never treat comparison weights as a landing-safety score.

## Repository maintenance

- [x] Generated `dist/` and `build/` files were removed from current Git tracking and should remain ignored.
- [ ] Inspect legacy/backup scripts before deleting or archiving; they may contain historical test fixtures or recovery points.
- [ ] Add a reproducible dependency lock / explicit desktop requirements after confirming package compatibility.
- [ ] Consider an automated Windows workflow that builds and smoke-tests the standalone ZIP on each tagged release.
- [ ] Review historical commits for accidentally committed private paths or oversized Git LFS objects. `.gitignore` does not rewrite history.
- [ ] Establish project licence/permissions; `pyproject.toml` currently declares an unlicensed prototype. Choose a licence deliberately before inviting broad reuse.

## Issue reporting

Report bugs with the app version/tag, region, selected candidate row and column, whether NASA rasters are installed, error text/log, and the Windows version. Do not include personal directories or sensitive information in public issue attachments.
