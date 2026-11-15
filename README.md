# SelenEkto

**A slope-first lunar south-pole terrain explorer and research-preview desktop app.**

SelenEkto is a Windows application for exploring NASA lunar terrain products, comparing named candidate locations, and investigating preliminary terrain-horizon and solar-illumination estimates. It includes an offline library of **24 slope previews**; full-resolution lunar raster files are optional and downloaded separately for detailed analysis.

> **Research preview, not operational mission-planning software.** Lunar coordinate-frame alignment, local terrain horizon assumptions and candidate-level illumination predictions still require independent scientific validation. A reported slope or comparison score is not a landing-safety determination.

## Download for Windows

**[Get the Windows portable ZIP from Releases](https://github.com/ApolloN1205/SelenEkto/releases)**.

1. Open the release's **Assets** section and download the actual application ZIP (not GitHub's automatically generated **Source code (zip)**).
2. Right-click the ZIP and choose **Extract All**.
3. Open the extracted `SelenEkto` folder and double-click `SelenEkto.exe`.
4. Keep the executable and its `_internal`, `src`, `scripts` and `data` folders together.

The portable distribution should not require separate Python, PowerShell, Git or Git LFS installations. Windows may display an unfamiliar-publisher warning for an unsigned build; do not disable security software to run it.

## Features

- **Explorer:** interactive lunar terrain with slope as the default layer
- **Data Library:** compact offline slope previews and selective downloads of detailed NASA terrain rasters
- **Candidates:** named locations and raster-derived metrics
- **Compare:** side-by-side comparisons and adjustable preference weights, with no compulsory winner
- **Illumination:** preliminary candidate terrain-horizon calculations and a NASA/JPL Horizons solar timeline
- **Settings:** dark Obsidian or Graphite with configurable accent colours including Aurora LOLA and Crimson

**Known data exclusions:** LM8, Site20 and Site23 are omitted from the usable catalogue because their data are incomplete or unverified. Original scientific source files are not intentionally deleted.

**Known issue:** the candidate-specific JPL solar workflow has not yet been confirmed end-to-end in the packaged release. A separate reference-site API test succeeded; this does not certify the complete feature. See [release checks and known limitations](docs/RELEASE_CHECKLIST.md).

## Source repository

The source and tests are in [`SelenEkto_Data_Infrastructure/`](SelenEkto_Data_Infrastructure/). A useful starting point is its [developer guide](SelenEkto_Data_Infrastructure/README.md).

- `src/selenekto_data/` — NASA catalogue, terrain, horizon and solar calculations
- `src/selenekto_v2/` — PySide6 interface and comparison/data library
- `scripts/` — launch, download, validation and release utilities
- `tests/` — automated regression tests
- `data/catalog/` — lightweight metadata and slope previews

Generated `dist/`, `build/`, `.venv/`, local NASA GeoTIFFs and private settings are intentionally not version-controlled. **GitHub Releases** host compiled Windows applications; **Tags** mark source-code versions.

## Credits and provenance

NASA lunar terrain products and NASA/JPL Horizons underpin the research features. See the project's [data-source audit](SelenEkto_Data_Infrastructure/DATA_SOURCE_AUDIT.md) for provenance and limitations. SelenEkto is an independent educational development project, not an official NASA or JPL application.

## Project status

**Public research preview**, under active development. Please use [GitHub Issues](https://github.com/ApolloN1205/SelenEkto/issues) to report reproducible bugs, including the exact version, selected lunar region and error message.
