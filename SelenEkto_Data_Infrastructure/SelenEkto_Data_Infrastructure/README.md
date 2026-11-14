# SelenEkto scientific data layer

**Version:** 0.1.0  
**Prepared:** 14 November 2026  
**Purpose:** A starter data infrastructure for the SelenEkto Lunar Landing Site Navigator.

This package gives the team a sourced 13-region location catalogue, an explicitly verified PGDA download register, a safe resumable downloader, checksums and acquisition logs, basic registry validation, optional GeoTIFF metadata inspection, and a JPL Horizons observer-query client.

## Important status statement

This package does **not** include NASA binary datasets. The execution environment used to create it had no outbound DNS/network access, so no real LOLA raster was downloaded and no live Horizons query was executed here. The source links and product filenames below were taken from the official NASA/PGDA pages and are recorded as such. A file is marked downloaded only after the downloader succeeds on your computer.

The included test fixtures are synthetic and clearly labelled. Passing the tests does not prove the astronomical or terrain outputs against live NASA data.

## What is included

- `data/catalog/landing_sites.json`: all 13 Artemis III candidate-region reference points, with source metadata.
- `data/catalog/landing_sites.csv`: a human-readable export of the same list.
- `data/catalog/pgda_5mpp_sites.json`: six site sections explicitly listed on PGDA's high-resolution 5 m/pixel landing-site download index.
- `data/catalog/pgda_product78_inventory.json`: 27 site/product families listed by PGDA Product 78. Entries are explicitly catalogue-only until individual downloadable files are verified.
- `data/catalog/sources.json`: source register.
- `data/manifests/datasets.json`: 36 explicit product records (six file types for each of the six PGDA 5mpp site sections).
- `src/selenekto_data`: catalogue, registry, download, validation, raster-inspection and Horizons modules.
- `tests/`: automated tests using local/synthetic fixtures only.

## Verified reference points

Coordinates are from NASA's **Moon to Mars Lunar Surface Data Book**, M2M-30044, effective 18 March 2025, Appendix A, Table A2.1-1, page 75. The table states that coordinates were generated from PGDA South Pole LOLA DEM files and that centre points of the original polygons are accurate to 5–10 m.

These are **representative region-centre coordinates**, not exact mission landing points, rover positions, or proof of landing safety. NASA's 2022 announcement describes each candidate region as approximately 15 km × 15 km and each potential landing site as a smaller area within it.

The values are preserved as printed in the NASA table. The table does not label the longitude sign convention in its column heading. JPL Horizons requires east longitude for lunar topocentric coordinates. The Horizons client therefore requires an explicit `--longitude-east-deg` value and will not silently convert a catalogue longitude. Confirm the source convention and reference frame before production use.

## PGDA product coverage

The official PGDA 5mpp download index explicitly lists these six site sections and six named file products per section:

| PGDA site | Region label on PGDA page | Candidate-region relationship |
|---|---|---|
| Site01 | Connecting Ridge | Connecting Ridge (R01/Site01) |
| Site04 | Shackleton Rim | Additional named feature; not one of the original 13 in NASA's 2022 list |
| Site07 | Peak near Shackleton | Peak Near Shackleton (R07/Site07) |
| Site11 | de Gerlache rim | M2M shorthand R11/Site11 is de Gerlache Rim 1 |
| Site20 | Leibnitz beta plateau | Leibnitz Beta Plateau (R20/Site20) |
| Site23 | Malapert massif | Malapert Massif (R23/Site23) |

Each section explicitly lists LDEM, XYZI, LDEC, slope, total Z uncertainty and slope uncertainty. The page states the raster products (except point clouds) are 5 m/pixel GeoTIFFs using south polar stereographic X/Y coordinates in metres, MOON_ME, associated with ephemeris DE421. Exact projection parameters, pixel registration, NoData values and any product-specific units must still be confirmed from the linked README and each file's metadata.

PGDA Product 78 lists 27 site/product families, including other Artemis-region shorthand codes. This package records those 27 as an **extended catalogue inventory** but does not manufacture 135 or 162 download links from a guessed URL template. The six-site download index is the only source used for the 36 direct product URLs in `datasets.json`.

## Installation

Use Python 3.10 or newer. From the repository root:

```bash
python -m venv .venv
```

If you unzip this package into your existing SelenEkto repository as `SelenEkto_Data_Infrastructure/`, install it from the repository root:

```powershell
python -m pip install -e ".\SelenEkto_Data_Infrastructure[geo,test]"
```

If you are working inside the data-layer folder itself, use `python -m pip install -e ".[geo,test]"`. Windows PowerShell virtual-environment setup:

macOS/Linux, from your existing repository root:

```bash
python -m pip install -e "./SelenEkto_Data_Infrastructure[geo,test]"
```

If working inside the data-layer folder itself, use `python -m pip install -e ".[geo,test]".

If rasterio installation fails on your machine, install the base package and tests first with `python -m pip install -e ".[test]"`. GeoTIFF inspection is optional and requires rasterio/GDAL compatibility with your Python environment.

## Commands

Run commands from the SelenEkto repository root after installing the nested package. The package locates its bundled data root automatically; set `SELENEKTO_ROOT` if you relocate the catalogue.

```bash
# List the 13 sourced region reference points
python -m selenekto_data list

# List all explicit PGDA direct-product records
python -m selenekto_data products

# Show which registered binary files are present locally
python -m selenekto_data status

# Validate location and product registries and check checksums of downloaded files
python -m selenekto_data validate

# Regenerate the CSV catalogue from the JSON source of truth
python -m selenekto_data build-catalog

# Download only the Site01 elevation DEM (one file; default 500 MiB cap)
python -m selenekto_data fetch --site Site01 --kind ldem

# Download all explicitly listed files for a site (each file still has its own cap)
python -m selenekto_data fetch --site Site07 --kind all

# Inspect a downloaded GeoTIFF without modifying it
python -m selenekto_data inspect-raster data/raw/lola/Site01/Site01_final_adj_5mpp_surf.tif
```

### Download safeguards

- HTTPS only.
- Official-source host allowlist.
- Default limit: 500 MiB **per file**.
- Content-Length checked before transfer when available.
- Streaming byte limit enforced even if Content-Length is absent or inaccurate.
- Partial `.part` files can resume when the server supports HTTP Range.
- A server that ignores Range causes a safe restart, not an append.
- SHA-256 calculated after a successful download.
- A successful download is recorded in `acquisition_log.json` and in the dataset registry.
- A failed/incomplete download is never promoted to a final file.

Do not raise the cap for a large mosaic or point cloud without checking the source size and agreeing on storage first. Large raw files are excluded from ordinary Git by `.gitignore.append`.

## JPL Horizons

The client requests an observer ephemeris from a user-defined lunar surface site using:

- Target `10` for the Sun, `399` for Earth.
- `CENTER=coord@301` (user-defined location on the Moon).
- `COORD_TYPE=GEODETIC`.
- `SITE_COORD=longitude_east_deg,latitude_deg,altitude_km`.
- `QUANTITIES=4` (apparent azimuth/elevation).
- `TIME_TYPE=UT` and explicit UTC input timestamps.

Example **only after confirming the source longitude convention**:

```bash
python -m selenekto_data horizons \
  --target sun \
  --latitude-deg -89.4632 \
  --longitude-east-deg 222.51 \
  --altitude-km 0 \
  --start 2026-11-14T00:00:00Z \
  --stop 2026-11-14T02:00:00Z \
  --step 10m
```

The example uses `222.51° E`, equivalent to `-137.49°` **only if** the source's negative value is confirmed to mean signed east-positive longitude. The client deliberately requires an east-positive [0, 360) longitude. It does not infer the convention from the site record.

JPL's manual states that lunar non-Earth sites use the Moon mean-Earth / DE421 convention and that the user-defined geodetic coordinate triplet is east longitude (degrees), latitude (degrees), altitude above reference ellipsoid (km). It also states that refraction is not modelled for non-Earth observers. Quantity 4 returns a celestial direction relative to Horizons' local horizon, **not** a terrain-obstructed visibility result. SelenEkto still needs to compare that direction against a local horizon calculated from LOLA terrain.

A zero altitude is the nominal reference-surface default in this prototype, not an extracted local surface elevation. Replace it with a defensible value when the exact point is sampled from a DEM and its vertical reference is reconciled.

The cache stores raw provider output and parsed rows under `data/cache/horizons/`. This directory is gitignored.

## What is not implemented yet

This package is a data foundation, not a finished scientific engine. It does not yet:

- Download NASA binary data in this environment.
- Perform lunar polar stereographic-to-body-fixed coordinate transformations.
- Sample a DEM to get exact elevation at a site centre.
- Calculate a topographic horizon profile.
- Compute terrain-shadowed Sun/Earth visibility.
- Compute solar-array wattage or a radio link budget.
- Implement a SPICE provider.
- Guarantee offline ephemeris availability.
- Verify Horizons through a live network query in this creation environment.

The next sensible step is to install the package on a networked team computer, fetch one LDEM under the default cap, inspect the GeoTIFF header, read the PGDA README, then issue a live Horizons request after confirming coordinate convention.

## Tests

```bash
pytest
```

Tests validate catalogue shape, selected coordinates against the NASA table, the six-site PGDA product registry, synthetic Horizons parsing, coordinate-input guards and checksum checking. They do not count as a live external-service test or scientific validation against real terrain data.

## Git integration

The package includes a nested `.gitignore` that applies within this folder. If you later move `data/raw/` or `data/cache/` to the repository root, merge the corresponding ignore patterns into the repository-level `.gitignore` rather than replacing that file. Commit code, catalogues, manifests, tests and documentation. Do not commit raw NASA DEMs or the ephemeris cache to ordinary Git history.
