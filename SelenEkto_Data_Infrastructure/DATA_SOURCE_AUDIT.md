# SelenEkto data source audit

**Checked:** 14 November 2026  
**Purpose:** Separate source-verified records from assumptions and unacquired data.

## 1. NASA Artemis candidate regions

**Source:** NASA, “NASA Identifies Candidate Regions for Landing Next Americans on Moon”, 19 August 2022.  
URL: https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/

The announcement names the 13 Artemis III candidate regions. It says each region is approximately 15 × 15 km and each potential landing site within it is approximately a 100 m radius. The list is the challenge's 13-region reference set, not a guarantee that all named regions currently have matching downloadable high-resolution DEMs.

## 2. Candidate-region reference coordinates

**Source:** NASA Moon to Mars Lunar Surface Data Book, M2M-30044, effective 18 March 2025.  
URL: https://ntrs.nasa.gov/citations/20250002845  
Table A2.1-1, page 75.

The table's preceding note says coordinates were generated from DEM files on the PGDA South Pole LOLA DEM website and that centre points of the original polygons are accurate to 5–10 metres. The table includes shorthand codes and the following matching records among its 26 features:

| NASA 2022 candidate region | M2M-30044 shorthand | Latitude | Longitude as published |
|---|---|---:|---:|
| Faustini Rim A | LM7 | -87.8897 | 90 |
| Peak Near Shackleton | R07 / Site07 | -88.8110 | 123.6901 |
| Connecting Ridge | R01 / Site01 | -89.4632 | -137.49 |
| Connecting Ridge Extension | SL3 | -89.0324 | -101.999 |
| de Gerlache Rim 1 | R11 / Site11 | -88.6834 | -67.9321 |
| de Gerlache Rim 2 | SL2 | -88.2300 | -64.6284 |
| de Gerlache-Kocher Massif | R42 / Site42 | -85.8296 | -116.322 |
| Haworth | Haworth | -86.7639 | -22.777 |
| Malapert Massif | R23 / Site23 | -85.9948 | -0.23578 |
| Leibnitz Beta Plateau | R20 / Site20 | -85.4266 | 31.74276 |
| Nobile Rim 1 | R06 / Site06 | -85.4381 | 37.36667 |
| Nobile Rim 2 | DM2 | -83.9540 | 58.82206 |
| Amundsen Rim | DM1 | -84.2287 | 69.44396 |

The coordinate table does not state a longitude direction in its column heading. The catalogue preserves the printed values and requires verification of longitude convention before feeding them to Horizons or transforming between frames.

## 3. PGDA explicit 5mpp asset index

**Source:** NASA GSFC Planetary Geodynamics Data Archive, “South Pole Landing Site LOLA DEMs”.  
URL: https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/

This page explicitly lists six site sections: Site01, Site04, Site07, Site11, Site20 and Site23. It lists six products under each: LDEM, XYZI, LDEC, slope, total Z uncertainty and slope uncertainty. The resulting 36 product records have filenames and URLs transcribed from this page.

The page states that the non-XYZI files are 5 m/pixel GeoTIFFs with south polar stereographic X/Y coordinates in metres, MOON_ME reference frame associated with ephemeris DE421. The page's short description does not replace examination of the product README or actual file headers. Exact projection parameters, pixel registration, vertical reference, NoData and product units must be checked from the file itself.

### Site-to-region correspondence

- Site01 = Connecting Ridge = R01/Site01.
- Site07 = Peak near Shackleton = R07/Site07.
- Site11 = de Gerlache rim; M2M table identifies R11/Site11 as de Gerlache Rim 1. The PGDA short label is less specific, so the mapping is marked as a shorthand match.
- Site20 = Leibnitz Beta Plateau = R20/Site20.
- Site23 = Malapert Massif = R23/Site23.
- Site04 = Shackleton Rim = R04/Site04, a named feature outside the original 13-region list.

## 4. PGDA broader product family inventory

**Source:** NASA GSFC PGDA Product 78, “High-Resolution LOLA Topography for Lunar South Pole Sites”.  
URL: https://pgda.gsfc.nasa.gov/products/78

The page's available catalogue text lists 27 site/product families: Site01, Site04, Site06, Site07, Site11, Site20, Site20v2, Site23, Site42, Haworth, Shoemaker, DM1, DM2, SL2, SL3, NPA, NPB, NPC, NPD and LM1–LM8.

This package records those names in `pgda_product78_inventory.json`. It intentionally does not manufacture individual download URLs for every family. Those links should be added only after the product page or underlying archive is checked directly.

## 5. JPL Horizons observer query

**API documentation:** https://ssd-api.jpl.nasa.gov/doc/horizons.html  
**System manual:** https://ssd.jpl.nasa.gov/horizons/manual.html

The API supports observer ephemerides. The manual documents user-defined non-Earth topocentric sites where the body has a rotation model. Moon code 301 can be used with `coord@301`; the geodetic coordinate triplet order is east longitude degrees, latitude degrees, altitude above reference ellipsoid in kilometres. The manual says lunar surface coordinates use Mean Earth of DE421. Quantity 4 is the observer apparent azimuth/elevation quantity.

The manual also says refraction is not modelled for non-Earth sites. This package does not yet have a successful live query recorded; use the CLI from a networked machine and verify the returned header before treating the parsed output as accepted.

## 6. Explicitly not claimed

- No raw NASA files are included in this package.
- No DEM file sizes are recorded because they were not retrieved in this execution environment.
- No file checksum is populated before download.
- No actual DEM has been raster-inspected here.
- No Horizons live query has been completed here.
- No terrain horizon or illumination result has been calculated.
- Product 78 inventory entries are not all direct-file-verified.
