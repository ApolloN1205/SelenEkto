# SELENEKTO — MASTER PROJECT DOSSIER
### Lunar Landing Site Navigator · 2026 NASA International Space Apps Challenge

| | |
|---|---|
| **Version** | 0.1 (first research pass) |
| **Research / access date** | 2026-11-13 (all "accessed" dates below refer to this unless stated) |
| **Status** | Working document. Must be re-verified item by item (see §20 "Verification Debt") |
| **Audience** | Team (4 students), future frontend developer, reviewers/judges, a new Claude session |

> **READ THIS FIRST — HONESTY STATEMENT**
> This dossier was produced in one research session with **limited tool access**: web search and page fetch worked; the official challenge page blocked automated access (robots.txt); there was **no GitHub repository access** and **no network from the sandbox**, so nothing was downloaded, run or tested.
> Every claim carries a status tag (§1.2). Anything tagged `VERIFIED` was read from a source during this session and has a link. Anything from background knowledge is tagged `PROPOSED` or `UNDER INVESTIGATION` and **must be checked before it is relied on**. Nothing here has been committed to Git.

> **⚠ TIMING ALERT — VERIFIED.** NASA's own page says the 2026 Space Apps Challenge is a two-day event on **Saturday 14 and Sunday 15 November 2026** ([NASA Science](https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/); also [Astronet](https://astronet.pl/wydarzenia/nasa-space-apps-challenge-2026-juz-w-listopadzie-zapisy-trwaja/), [The Recursive](https://www.therecursive.com/nasa-space-apps-challenge-2026-where-to-join-it-in-cee/)). Today is 13 November. **The hackathon starts tomorrow.** §14.2 gives a 48-hour plan; the 11-phase roadmap in §14.1 is the longer-term plan if the project continues beyond the event.

---

## Table of contents

1. [Document conventions](#1-document-conventions)
2. [Executive summary](#2-executive-summary)
3. [Project scope and principles](#3-project-scope-and-principles)
4. [Official challenge requirements and judging](#4-official-challenge-requirements-and-judging)
5. [NASA data catalogue](#5-nasa-data-catalogue)
6. [Coordinate systems and reference frames](#6-coordinate-systems-and-reference-frames)
7. [Time systems](#7-time-systems)
8. [Celestial geometry (Sun and Earth)](#8-celestial-geometry-sun-and-earth)
9. [Terrain horizon, illumination, Earth visibility](#9-terrain-horizon-illumination-earth-visibility)
10. [Uncertainty and accuracy](#10-uncertainty-and-accuracy)
11. [Technology evaluation](#11-technology-evaluation)
12. [Backend architecture](#12-backend-architecture)
13. [Future API contract](#13-future-api-contract)
14. [Development roadmap (11 phases) and 48-hour plan](#14-development-roadmap)
15. [Team workflow and Git](#15-team-workflow-and-git)
16. [Learning programme](#16-learning-programme)
17. [Testing and validation](#17-testing-and-validation)
18. [Offline/online operation](#18-offlineonline-operation)
19. [Risk register](#19-risk-register)
20. [Verification debt, unresolved questions](#20-verification-debt-and-unresolved-questions)
21. [Judging strategy](#21-judging-and-presentation-strategy)
22. [Human ownership and AI policy](#22-human-ownership-and-ai-policy)
23. [Final checklist](#23-final-actionable-checklist)
24. [Glossary](#24-glossary)
25. [References](#25-references)

---

## 1. Document conventions

### 1.1 Evidence classes
Every important statement belongs to one of: **Confirmed scientific fact**, **Published research finding**, **Official NASA data/documentation**, **Engineering recommendation**, **Proposed project assumption**, **Unverified possibility**.

### 1.2 Status tags
| Tag | Meaning |
|---|---|
| `VERIFIED` | Read from the cited source during this session |
| `RECOMMENDED` | Our engineering advice, reasoned but not externally tested |
| `PROPOSED` | A project decision/assumption the team may change |
| `UNDER INVESTIGATION` | Believed true from background knowledge or partial evidence; **verify before use** |
| `UNAVAILABLE` | Tried and could not be accessed |
| `NOT REQUIRED FOR INITIAL IMPLEMENTATION` | Deliberately deferred |

### 1.3 Rules for contributors
- Never paste a number, URL, kernel filename or version into code without a recorded source and access date.
- Illustrative examples in this document are **not real results**. They are labelled.
- If two calculations disagree, do not call either wrong until frame, time scale, aberration correction and body-radius conventions are compared (§17.3).

---

## 2. Executive summary

**Problem.** At the lunar south pole the Sun skims the horizon and Earth sits low in the sky or below it, so landing-site viability depends on *where* and *when*. Sun and Earth elevation, azimuth and the local terrain horizon decide illumination and direct-to-Earth line of sight.

**Product.** SelenEkto computes, for a chosen lunar location and time range: Sun and Earth azimuth/elevation, the terrain-limited horizon, illumination and Earth-visibility windows (including time to next sunset/Earthset), and compares several site–date scenarios.

**Key technical insight.** The hard part is not the astronomy; it is making three independent things agree: (1) **ephemeris** (SPICE), (2) **terrain** (LOLA DEMs on a south-polar stereographic grid), (3) **frame/coordinate conventions** between them. A mismatch of only ~1 arcsecond in orientation equals ~8.4 m on the Moon's surface (1″ × 1,737.4 km), larger than one 5 m DEM pixel. See §6.5.

**Recommended core stack** (`RECOMMENDED`): Python + NumPy + SpiceyPy (SPICE kernels for Sun/Earth/Moon orientation) + Rasterio (read GeoTIFF DEMs) + Pydantic + pytest; FastAPI added when the schema is stable. No C++, ML or microservices.

**Recommended first data** (`RECOMMENDED`): one small PGDA 5 m site product (e.g. `Site01`, the "Connecting ridge") plus its uncertainty rasters — not the 3.3 GB 87–90°S mosaic.

**What we will *not* claim:** electrical power output (needs panel assumptions) or a working radio link (geometry ≠ link budget).

---

## 3. Project scope and principles

**Primary geography:** lunar south pole. **Primary users:** mission planners/engineers; secondary: lay audience.

Principles (as set by the team brief): scientific correctness before appearance; backend first; frontend independence; explainability; appropriate complexity; reproducibility; team ownership.

### 3.1 Minimum viable scientific product (MVSP) — `PROPOSED`
**Must have (core):**
1. Input: a site (selenographic lat/lon or a named site), a UTC time range, step size.
2. Sun azimuth/elevation and Earth azimuth/elevation from SPICE (geometric, light-time corrected).
3. Terrain horizon profile (elevation angle vs azimuth) from a LOLA DEM at the site.
4. Boolean/fractional Sun visibility and Earth visibility vs time (disk centre first, partial disk second).
5. Event extraction: sunrise/sunset, Earthrise/Earthset, window durations, time-to-next-event.
6. Comparison of ≥2 site–date scenarios in one structured result.
7. Metadata: units, time scale, frame, kernel and DEM identifiers on every result.

**Should have:** uncertainty indication using PGDA uncertainty rasters/clones; observer height parameter (PGDA itself reports illumination at 1 m and 5 m heights, so this matters).

**Future (`NOT REQUIRED FOR INITIAL IMPLEMENTATION`):** power model with explicit hardware assumptions, link budget, 3-D ray tracing, many-site screening, ML.

---

## 4. Official challenge requirements and judging

**Source status.** The official page (<https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/>) returned `ROBOTS_DISALLOWED` to the fetch tool → **`UNAVAILABLE` to this session**. The requirement list and judging criteria below come from the **team's own brief** (which states they were taken from the challenge) and have **not been independently re-verified**. **Action (owner: coordinator): open the page in a browser, compare line by line, and record any difference here.**

### 4.1 Requirements (from brief; `UNDER INVESTIGATION` until compared)
| # | Requirement | Class | Where addressed |
|---|---|---|---|
| 1 | Interactive location selection | Frontend; backend supplies site catalogue & custom lat/lon validation | §13 |
| 2 | Compare multiple landing sites | **Core** | §12 comparison engine |
| 3 | Flexible dates/times | **Core** | §7, §13 |
| 4 | Sun position relative to horizon | **Core** | §8, §9 |
| 5 | Earth position relative to horizon | **Core** | §8, §9 |
| 6 | Solar illumination & power *potential* | Core = illumination; power = **optional** | §9.4 |
| 7 | Direct-to-Earth geometric visibility | **Core** | §9.5 |
| 8 | Time remaining before sunset/Earthset | **Core** | §9.6 |
| 9 | Temporal changes | **Core** | §12 |
| 10 | Terrain/local horizon effects | **Core** (this is the differentiator) | §9.1 |
| 11 | Accessibility/understandable presentation | Frontend phase; backend supplies plain-language summaries | §13 |

### 4.2 Judging framework (from brief) and evidence plan
| Criterion | How to demonstrate excellence | Evidence to show |
|---|---|---|
| **Impact** | Show a concrete planner question answered in seconds ("which of these 3 rim sites has the longest Earth+Sun overlap in week X?") | Worked comparison; honest statement of who benefits |
| **Creativity & innovation** | One tool that fuses ephemeris + real terrain horizon + comparison, instead of separate tools | Side-by-side with the manual workflow (QuickMap/Moon Trek/Horizons) |
| **Validity & feasibility** | Reproducible calculations validated against independent references; stated uncertainty | Test report: SPICE vs Horizons agreement, synthetic-terrain tests, DEM-uncertainty sensitivity |
| **Relevance & NASA data** | Use LOLA/PGDA DEMs, SPICE/NAIF, Horizons for validation, with provenance | Provenance table in the app and the dossier |
| **Communication & storytelling** | Clear narrative from problem → method → result → limits | 1-page method diagram, demo, honest limitations slide |

### 4.3 Submission/eligibility
Event dates `VERIFIED` (above). Submission deadlines, team-size rules, AI-use rules, licensing and judging timeline: **`UNVERIFIED`**. Read the Space Apps Participant FAQs/Guides (linked from <https://www.spaceappschallenge.org/>) *today* and paste the rules into §20.

---

## 5. NASA data catalogue

### 5.1 Quick decision table

| Tier | Resource | Type | Why | Start with |
|---|---|---|---|---|
| **1** | NAIF SPICE kernels (SPK planets, LSK, lunar PCK/FK) | Original data (ephemeris) | Sun/Earth/Moon positions & Moon orientation, offline | Yes |
| **1** | PGDA 5 m LOLA site DEMs (`Site01` etc.) | Derived products from original LOLA altimetry | Terrain horizon at landing-site scale; uncertainty included | Yes — 1 site |
| **1** | JPL Horizons | API service | Independent reference for validation (not production) | Yes, for tests |
| **2** | PGDA 87–90°S mosaic (`ldem_87s_5mpp`) | Derived product | Arbitrary custom coordinates near pole | Later; 3.3 GB |
| **2** | PGDA uncertainty rasters + 100 clones | Derived | Uncertainty propagation | After MVP |
| **2** | PGDA slope / LDEC count maps | Derived | Quality masks | After MVP |
| **2** | PDS LRO LOLA archive (original data) | Original | Provenance; alternative DEMs | Reference |
| **3** | LROC/QuickMap imagery, Diviner, LEND, Mini-RF, LAMP, Radio Science | Original/visualisation | Context only | No |
| **Ref** | QuickMap, Moon Trek | Visualisation platforms | Cross-checks, exploration — **not** primary data archives | For comparison |
| **Ref** | CSA lunar pages | Context | Narrative only | No |

### 5.2 Tier 1 records

#### 5.2.1 PGDA — High-Resolution LOLA Topography for Lunar South Pole Sites — `VERIFIED`
- **Product page:** <https://pgda.gsfc.nasa.gov/products/78> (accessed 2026-11-13). Data root: <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/>. README: <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README> (listed on the page; **not read** this session).
- **Provider:** NASA GSFC Planetary Geology, Geophysics and Geochemistry Laboratory; author Michael K. Barker; curator Erwan Mazarico.
- **Class:** *Derived* product (built from original LRO-LOLA laser-altimetry tracks, adjusted).
- **Per-site files** (page lists these for each site): `*_final_adj_5mpp_surf.tif` (LDEM, surface height Z in m), `*_final_adj.xyzi` (adjusted point cloud), `*_final_adj_5mpp_ldec.tif` (count of LOLA spots per pixel), `*_slp.tif` (slope, degrees), `*_toterr.tif` (total Z uncertainty, m, formally RMS), `*_slperr.tif` (slope uncertainty, degrees, RMS), `*_ROIs.tgz` (GIS shapefiles; not listed for every site), and `Clones/*_0001…0100_err.tif` (100 clones).
- **Grid/CRS:** 5 m/pixel GeoTIFFs, **south polar stereographic X/Y in metres, MOON_ME reference frame of ephemeris DE421** (XYZI and ROI files excluded from the GeoTIFF statement).
- **Coverage — sites listed** (page): Site01 Connecting ridge; Site04 Shackleton rim; Site06 Nobile rim 1; Site07 Peak near Shackleton; Site11 de Gerlache rim; Site20 and Site20v2 Leibnitz beta plateau; Site23 Malapert massif; Site42 de Gerlache–Kocher massif; Haworth; Shoemaker; DM1 Amundsen rim; DM2 Nobile rim 2; SL2 de Gerlache rim; SL3 Connecting ridge extension; NPA Cabeus exterior wall 1; NPB Amundsen 1; NPC Idel'son L crater 1; NPD Malapert crater 1; LM1 Shackleton Rim B; LM2–LM6 and LM8 Shoemaker rims; LM7 Faustini Rim A. Numbering follows Mazarico et al. (2011). Note: the page text was truncated at "Shoemaker" in the fetch, so per-site link existence beyond Shoemaker is **not individually checked**.
- **Update history (page):** Site42/DM1/SL2 added 2021-04-26; NPA/NPB 2021-05-24; NPC/NPD 2021-06-14; LM1–LM8 2021-08-10; Site20v2 2022-08-15. "Latest verified release" = no newer entry visible on the page; **publication date of the underlying paper: 2021 (Barker et al., PSS 203, 105119).**
- **Quality figures (page text):** track geolocation uncertainty ~10–20 cm horizontal, ~2–4 cm vertical; **~90 % of 5 m pixels are interpolated** (large gaps between LOLA tracks); median RMS Z error ~0.30–0.50 m; median RMS slope error ~1.5–2.5°; interpolation error grows with distance from the pole at fixed pixel scale (lower point density).
- **Authors' stated purpose of clones:** a statistical ensemble with similar error properties to study height, slope and **illumination** uncertainty. Directly relevant to SelenEkto §10.
- **Size / licence / access:** per-site file sizes **NOT VERIFIED**; access appears anonymous HTTPS (no login seen); licence/attribution: not stated on page beyond NASA reproduction guidelines — **UNDER INVESTIGATION**. Cite Barker et al. (2021).
- **Python:** Rasterio / GDAL, NumPy, PyProj.
- **Acquisition procedure** (`RECOMMENDED`): (1) read the README; (2) run `gdalinfo` or `rasterio.open()` on the remote URL using GDAL's `/vsicurl/` to read the header **before** downloading; (3) download only `Site01_final_adj_5mpp_surf.tif`, `_toterr.tif`, `_slp.tif`; (4) record SHA-256, byte size, date, URL in `data_manifest` (§18); (5) fetch ≥3 clones only when the uncertainty module is built.

#### 5.2.2 PGDA — South Pole LOLA DEM Mosaic (87–90°S) — `VERIFIED`
- **Page:** <https://pgda.gsfc.nasa.gov/products/81> (accessed 2026-11-13).
- **Construction:** 97 fields of 20×20 km with 2 km overlaps, each processed as in product 78, aligned by rigid 3-D translation, blended with cosine-taper weights. Overlap counts are therefore **non-integer**. Typical RMS residual vs individual fields **30–55 cm**.
- **Files and sizes (page):** `ldem_87s_5mpp.tif` **3.3 GB** (surface height Z in m, interpolation-filled); `ldem_87s_5mpp_hillshade.tif` 820 MB; `ldsm_87s_5mpp.tif` **4.9 GB** (slope, degrees); `ldec_87s_5mpp.tif` 140 MB (count map). URLs under <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/>.
- **CRS/grid:** 5 m/pixel, south polar stereographic X/Y in m, MOON_ME frame of DE421. **X/Y follow the Generic Mapping Tools "pixel-registered" convention — coordinates are pixel centres.** Must be honoured in the raster→coordinate transform (see §6.6).
- **Citation required:** Barker et al., 2021, *Improved LOLA Elevation Maps for South Pole Landing Sites: Error Estimates and Their Impact on Illumination Conditions*, Planetary & Space Science 203, 105119, <https://doi.org/10.1016/j.pss.2020.105119>.
- **Storage/processing implication:** the 5 m grid is far too large to load whole into RAM as float64 (the file is 3.3 GB on disk; in memory it can be larger, depending on dtype/compression — **uncompressed size NOT VERIFIED**). Use windowed reads (`rasterio.windows`), or crop a ~20–40 km tile around each site once and store the tile.
- **Recommendation:** Tier 2. Needed only for *custom* coordinates across the polar cap. Not needed for a MVP built on named sites.
- **Open question:** the mosaic ships no uncertainty raster on this page. Use the per-site `toterr` rasters where a site exists; for other places uncertainty is `UNAVAILABLE` from this product.

#### 5.2.3 NAIF SPICE — `PARTLY VERIFIED`
- **Site:** <https://naif.jpl.nasa.gov/>; lunar-mission listing <https://naif.jpl.nasa.gov/naif/data_lunar.html> (`VERIFIED`, accessed 2026-11-13): lists Apollo, Artemis Program (SPK), LADEE, **LRO (CK ×209, FK, IK in the primary directory)**, Lunar Orbiters, Lunar Prospector, SMART-1, etc. Note the table shows **no LSK/PCK/SPK counts for LRO** — LRO orbit SPKs may live elsewhere. For SelenEkto, mission spacecraft kernels are **not needed**; we need *generic* kernels.
- **Kernels we need (concepts, `UNDER INVESTIGATION` for exact files):**
  | Kernel | Role | Why |
  |---|---|---|
  | **LSK** (leap seconds, `.tls`) | UTC↔ET | Mandatory for time conversion |
  | **SPK** planetary/lunar ephemeris (`.bsp`, DE-series) | Positions of Sun, Earth, Moon | Core geometry |
  | **PCK** binary lunar orientation (`.bpc`) | Moon libration/rotation (principal-axes frame) | Core |
  | **FK** (frame definitions, `.tf`) | Defines Moon frames incl. MOON_ME and relation to MOON_PA | Core — *this is where the DE421-vs-DE440 frame question is settled* |
  | SCLK, CK | Spacecraft clocks/attitude | **Not required** |
- **Exact filenames/versions:** the generic-kernel directory <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/> was **not fetched** this session. Candidate names recalled from background knowledge (e.g. `naif0012.tls`, `de440s.bsp`, a `moon_pa_de440_…bpc` and a `moon_de440_…tf`) are **UNVERIFIED — open the directory listing and record the true current names, sizes and dates in the manifest. Do not copy the names from this dossier.**
- **The DE421/DE440 issue (critical, `UNDER INVESTIGATION`):** the PGDA DEMs are tied to **MOON_ME as defined with DE421**. A modern ephemeris (DE440) comes with its own lunar orientation and its own definition of the ME frame. These can differ slightly. **Phase 4 must quantify the difference** — preferably by using DE421-consistent kernels for terrain registration, or by computing the DE421↔DE440 ME offset and showing it is below the DEM's uncertainty. Do not assume equality.
- **Horizons vs SPICE:** Horizons is an online *service* that computes tables for you; SPICE is a *toolkit + data files* you run locally. SPICE is needed for offline, vectorised, reproducible production use; Horizons is ideal as an independent check.
- **SpiceyPy:** Python wrapper for CSPICE — <https://spiceypy.readthedocs.io/>. Fit for the ephemeris module. Install/compat details: §11.

#### 5.2.4 JPL Horizons — `PARTLY VERIFIED`
- **Web:** <https://ssd.jpl.nasa.gov/horizons/>; manual <https://ssd.jpl.nasa.gov/horizons/manual.html> (**not fetched**); API doc <https://ssd-api.jpl.nasa.gov/doc/horizons.html> (`VERIFIED` via search snippet).
- **Endpoint (`VERIFIED`):** `GET https://ssd.jpl.nasa.gov/api/horizons.api` with parameters such as `COMMAND`, `EPHEM_TYPE` (OBSERVER/VECTORS/ELEMENTS), `CENTER`, `COORD_TYPE` (GEODETIC or CYLINDRICAL), `SITE_COORD`, `START_TIME`, `STOP_TIME`, `STEP_SIZE`, `QUANTITIES`. File-based variant: `POST https://ssd.jpl.nasa.gov/api/horizons_file.api` (reported by a third-party reference, not by JPL directly).
- **Site coordinates (`VERIFIED` from JPL batch example text):** for `COORD_TYPE=GEODETIC`, `SITE_COORD` = {**east** longitude, latitude, height} with km and degrees. Quotes are required. `APPARENT` takes `AIRLESS` or `REFRACTED` — **always use `AIRLESS` for the Moon**.
- **Using a lunar surface point as observer (`UNDER INVESTIGATION`):** by analogy with Earth-site usage (`CENTER='coord@399'`), a lunar site would be `CENTER='coord@301'` with `SITE_COORD='lon,lat,alt'`. **Not tested.** First Horizons task for the team: reproduce a Sun az/el at a lunar site, then read the header block to identify the frame, radius and lat/lon conventions Horizons actually uses.
- **Role:** Tier-1 **validation** source, not production (network dependence, rate limits unknown, not vectorisable).
- **Apparent vs geometric (`Confirmed concept`):** *geometric* = true position at the instant; *astrometric* = corrected for light-time; *apparent* adds aberration (and deflection, and for Earth sites refraction). On the Moon there is no refraction. For "is the Sun visible now," use **light-time + stellar-aberration corrected** directions (SPICE `LT+S`); the difference vs geometric is tiny for the Sun's disk size but must be consistent between SPICE and Horizons when comparing (§17.3).

### 5.3 Tier 2/3 and reference resources

| Resource | URL | Class | Note | Status |
|---|---|---|---|---|
| PDS Geosciences LRO | <https://pds-geosciences.wustl.edu/missions/lro/> | Original-data archive | LOLA/other RDRs; product IDs/versions **not fetched** | UNDER INVESTIGATION |
| Imbrium (MIT PDS node) | <https://imbrium.mit.edu/> | Archive mirror/portal | Not fetched | UNDER INVESTIGATION |
| PDS main | <https://pds.nasa.gov/> | Portal | Not fetched | UNDER INVESTIGATION |
| LRO instruments: LOLA, LROC, Diviner, LEND, Mini-RF, Radio Science, LAMP | via PDS above | Original | **Core relevance only LOLA** (topography; LROC for imagery context). Diviner = temperature, LEND = neutrons/hydrogen, Mini-RF = radar, LAMP = UV, Radio Science = gravity: *context*, not geometry | RECOMMENDED: Tier 3 |
| LROC QuickMap | <https://quickmap.lroc.asu.edu/> | Visualisation platform (ASU) | Exploration/cross-check of terrain/illumination. **Acquire LOLA data from PGDA/PDS, not by screenshots.** Export capabilities not tested | UNDER INVESTIGATION |
| NASA Moon Trek | <https://trek.nasa.gov/moon/> | Visualisation/analysis platform | Reference for expected outputs (profiles, lighting, line-of-sight). Account/export rules not tested | UNDER INVESTIGATION |
| CSA Moon exploration | <https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/> | Context | Storytelling only | NOT REQUIRED |
| USGS Astrogeology, LPI, Lunar South Pole Atlas, Artemis/CLPS docs | — | Context/docs | Not fetched; add only if needed | UNDER INVESTIGATION |

> **Visualisation ≠ archive.** QuickMap and Moon Trek *display* products derived from LRO and other data. Our scientific inputs come from PGDA/PDS/NAIF with recorded versions.

### 5.4 Data-management strategy (`RECOMMENDED`)
Keep `data/raw/` out of Git (add to `.gitignore`); commit only `data/manifest.yaml`. Each entry records: `id, source_url, retrieved_utc, bytes, sha256, product_version/release_note, crs, frame, ephemeris, units, nodata, processing_history[]`. Derived tiles are reproducible from raw via a documented command. Ship a **tiny sample** (e.g. a 2 km × 2 km crop, a few MB) so frontend developers and CI never need the big files. Licence of the crop: confirm before committing.

---

## 6. Coordinate systems and reference frames

### 6.1 Selenographic latitude/longitude
Latitude φ ∈ [−90°, 90°] (south negative); longitude λ ∈ [0°, 360°) east-positive or (−180°, 180°]. Conventions differ between data providers (east vs west positive for older sources). **Horizons expects east longitude** for `SITE_COORD` (`VERIFIED` above). **PROPOSED internal convention:** φ planetocentric degrees, λ **east-positive in (−180, 180]**, converted at the edges.

### 6.2 Planetocentric vs planetodetic
Planetocentric latitude is the angle at the body centre; planetodetic is the angle of the local ellipsoid normal. The Moon is nearly spherical (LOLA products use a sphere; the standard lunar reference radius is 1,737.4 km — `UNDER INVESTIGATION` for the exact value PGDA uses; read the README). Treat the Moon as a **sphere** and use planetocentric coordinates; document the choice and bound the error (flattening ~0.0012 ⇒ ≲ ~2 km radial difference between pole and equator; sub-degree latitude differences — *quantify in Phase 4*).

### 6.3 Mean Earth/Polar Axis (ME) vs Principal Axes (PA) frames
- **PA:** axes along the Moon's principal moments of inertia — the frame in which libration is naturally modelled in ephemerides.
- **ME:** axes defined by the mean Earth direction and mean rotation axis — the frame in which cartography (lat/lon) is conventionally given.
- The two are related by a **small fixed rotation** (of order a minute of arc, i.e. of order 0.5 km on the surface; `UNDER INVESTIGATION` — compute from the FK).
- SPICE: orientation comes from the lunar PCK (PA) and FK (links PA→ME). **Our DEM is in ME; the Sun/Earth directions must be rotated into ME**, not PA.

### 6.4 South polar stereographic projection
For a sphere of radius R, scale factor k₀ and central meridian λ₀, south-polar case (Snyder-style formulation, `UNDER INVESTIGATION` for the exact PGDA parameters — read GeoTIFF/README):

$$\rho = 2Rk_0\tan\!\left(\tfrac{\pi}{4}+\tfrac{\varphi}{2}\right),\quad x=\rho\sin(\lambda-\lambda_0),\quad y=\rho\cos(\lambda-\lambda_0)$$

Inverse: $\varphi = 2\arctan\!\left(\dfrac{\rho}{2Rk_0}\right)-\dfrac{\pi}{2},\ \ \lambda=\lambda_0+\operatorname{atan2}(x,y)$, with $\rho=\sqrt{x^2+y^2}$.

Symbols: φ latitude (rad, south negative); λ east longitude; R sphere radius (m); k₀ scale at the pole (often 1); ρ radial distance from the pole in the projection plane (m). **Check:** φ = −90° ⇒ ρ = 0 ✓.
**Warning:** orientation of the x/y axes relative to longitude, and k₀, differ between software. Verify with 3–4 known control points before trusting any transform (§17).

### 6.5 Why small mismatches matter (calculation, not a NASA result)
Arc length = R·θ. With R = 1,737.4 km: **1″ ≈ 8.4 m**; 0.1″ ≈ 0.84 m; 1′ ≈ 505 m. DEM pixel = 5 m; Barker et al. report ~0.3–0.5 m median Z error. A frame error of a few arcseconds shifts the DEM by tens of metres relative to the ephemeris, moving a terrain edge in azimuth/elevation and potentially converting "sunlit" to "shadowed" on narrow ridges. A sphere-radius mismatch of 1 km changes curvature drop at 10 km range by only ~0.06 % (1 km / 1,737 km; small), but a wrong *height reference* (sphere vs ellipsoid vs geoid-like) shifts all heights by metres to kilometres.

### 6.6 Raster georeferencing and pixel registration
GeoTIFF affine transform maps (col,row)→(x,y). **Pixel-is-point vs pixel-is-area** matters: PGDA states coordinates are pixel **centres** (GMT pixel registration, `VERIFIED` for the mosaic page). A GDAL/Rasterio transform assumes pixel-is-area (upper-left corner origin) unless the `AREA_OR_POINT=Point` tag is set. A half-pixel (2.5 m) error is small versus the frame issue but **must be checked** and covered by a test (§17.6).

### 6.7 Local tangent (ENU) frame
At site (φ, λ) in the body-fixed frame (unit vectors, columns of components X,Y,Z):

$$\hat u=(\cos\varphi\cos\lambda,\ \cos\varphi\sin\lambda,\ \sin\varphi)$$
$$\hat e=(-\sin\lambda,\ \cos\lambda,\ 0)$$
$$\hat n=(-\sin\varphi\cos\lambda,\ -\sin\varphi\sin\lambda,\ \cos\varphi)$$

For a unit direction $\hat s$ to a body (Sun/Earth) in the same frame:

$$\text{el}=\arcsin(\hat s\cdot\hat u),\qquad \text{az}=\operatorname{atan2}(\hat s\cdot\hat e,\ \hat s\cdot\hat n)\ \ (\text{0° = north, 90° = east})$$

Near the pole λ is ill-conditioned; this is fine for the *formula* (ê, n̂ are still defined for φ > −90°) but **exactly at φ = −90°** azimuth needs a convention. Treat sites at φ = −90° as `φ = −90°+ε` or define az relative to λ = 0; document it.

*Purpose/limits:* assumes a spherical local vertical; terrain-slope-tilted "up" is a different problem (panel tilt) and not modelled here.

---

## 7. Time systems

| Scale | What it is | Use for us |
|---|---|---|
| **UTC** | Civil time with leap seconds; discontinuous | User input/output only |
| **TAI** | Continuous atomic time; TAI − UTC = integer seconds (37 s since 2017-01-01 as last known to this author — *confirm from the LSK you load, do not hard-code*) | Intermediate |
| **TT** | Terrestrial Time = TAI + 32.184 s | Rarely needed |
| **TDB** | Barycentric dynamical time; differs from TT by a small periodic term (order of milliseconds) | Ephemeris argument |
| **ET** (SPICE) | Seconds past J2000 (2000-01-01 12:00 TDB) in TDB-like scale | **Internal time** |
| **JD / MJD** | Day counts | Display/interchange only |

**PROPOSED rule:** the API accepts and returns **ISO-8601 UTC strings with `Z`**; internally everything is a NumPy array of **ET seconds (float64)** produced by SPICE `str2et` using the loaded LSK. Never use naïve `datetime`, never mix local time. Conversions happen only in one module (`timeconv`).

**Sampling.** The Sun's disk is ~0.53° across; at the south pole the Sun moves slowly in elevation (the Moon rotates once in ~27.3 days ⇒ ~0.55° of azimuth change per hour), so minute-scale steps are *plenty* for disk-crossing events, but terrain-edge events (a sharp ridge occulting the Sun) may need finer steps. **PROPOSED:** coarse scan at 10–30 min, then bisection refinement of each event to a stated tolerance (e.g. 1 s). Validate by halving the step and checking events move less than the tolerance (§17.8).

**Error budget (illustrative reasoning).** 1 s of time error ≈ 0.00015° of sky motion in azimuth (360°/27.3 d ≈ 1.5×10⁻⁴ °/s) — negligible, except that *apparent* light-time (Earth ≈ 1.28 s away; Sun ≈ 499 s) must be treated consistently.

---

## 8. Celestial geometry (Sun and Earth)

**Purpose.** Obtain the direction from the site to the Sun and to Earth in the Moon's body-fixed ME frame, then convert to az/el (§6.7).

**Method (SpiceyPy, `PROPOSED`).**
1. Load kernels (LSK, SPK, lunar PCK, FK) via a metakernel (`furnsh`).
2. `et = str2et(utc_string)`.
3. Vector from Moon centre to the target in the ME frame with light-time and stellar aberration: `spkpos(target, et, 'MOON_ME', 'LT+S', 'MOON')`. (Frame name `MOON_ME` and availability depend on the FK loaded — **UNDER INVESTIGATION**; some FK versions provide additional ME variants.)
4. **Site offset matters:** the vector is from Moon *centre*; the site is displaced by ≈R from centre. For the Sun (1 AU) the parallax is ~R/1 AU ≈ 1.2×10⁻⁵ rad ≈ 2.4″ — small but not zero; for Earth (≈384,400 km) it is up to R/d ≈ 0.26° — **not negligible**. So compute site→target: $\vec r_{site\to target} = \vec r_{center\to target}-\vec r_{center\to site}$, with $\vec r_{center\to site}=(R+h)\hat u$ (R + surface height from DEM).
5. Normalise, apply §6.7.

**Variables.** et: seconds (ET); R: m; h: m above reference sphere; $\hat u$: unit up-vector; el, az: degrees.
**Assumptions.** Spherical Moon; site height from DEM; no refraction. **Limits.** Frame definition (§5.2.3); aberration choice; sphere radius consistency with DEM.
**Validation.** Compare with Horizons observer-table az/el at a lunar site with matching conventions (§17.3), and with a hand-built geometry test (site on the sub-Earth point ⇒ Earth elevation ≈ 90° at mean libration).

**Facts useful for sanity checks (`Confirmed concept`, approximate):** from the Moon, Earth subtends roughly 1.9° (diameter) and the Sun ~0.53°; Earth stays near a fixed direction in the lunar sky due to tidal locking, swinging by a few degrees through **libration** (~±6–8° in latitude and longitude); at the south pole Earth is near the horizon and can be partly or wholly occulted by terrain; the Sun's elevation stays within roughly ±1.5° of the horizon (from the lunar axial tilt of ~1.5°). The team should *reproduce* these from SPICE as a first correctness check rather than trusting this paragraph.

---

## 9. Terrain horizon, illumination, Earth visibility

### 9.1 Terrain horizon profile
**Purpose.** For each azimuth α, find the maximum elevation angle of terrain as seen from the observer; a body is visible if its elevation exceeds the horizon at its azimuth (plus disk radius for partial visibility).

**Geometry (exact for a spherical Moon).** Observer O at radius $r_0=R+z_0+h_{obs}$, terrain point P at radius $r_P=R+z_P$, central angle θ between them (from great-circle distance $d=R\theta$ approx.). Elevation of P seen from O:

$$\varepsilon_P=\operatorname{atan2}\big(r_P\cos\theta-r_0,\ r_P\sin\theta\big)$$

Horizon at azimuth α: $H(\alpha)=\max_{d\in(0,d_{max}]}\varepsilon_P(d,\alpha)$. Flat-terrain approximation: $\varepsilon\approx\dfrac{z_P-z_0-h_{obs}}{d}-\dfrac{d}{2R}$; the last term is **curvature drop**: ≈ 28.8 m at 10 km (calculation: 10⁸ m² / (2×1.7374×10⁶ m)). Ignoring curvature overestimates obstruction for distant peaks, so include it.

**Variables.** R (m), $z_0$, $z_P$ (DEM heights, m), $h_{obs}$ (m, e.g. 1 m, 5 m — a design parameter), d (m), θ (rad), α (deg), $d_{max}$ (m; limited by tile size — a crop that is too small truncates distant horizons; **document $d_{max}$ per result**).
**Inputs.** DEM tile (§5), site (x,y) in raster coordinates via §6.4, $h_{obs}$, azimuth step (e.g. 0.5–1°), range step ≈ pixel size.
**Outputs.** Array H(α) in degrees + metadata (DEM id, $d_{max}$, interpolation).
**Implementation (`PROPOSED`).** For each α sample points along the ray in projected (x,y), interpolate Z with bilinear interpolation (SciPy `map_coordinates` or manual NumPy), compute ε, take max. Vectorise over α. Python/NumPy is sufficient for one site; **only if** many sites × fine azimuths proves too slow, consider Numba or C++ (§11).
**Assumptions/limits.** Projected-plane ray ≠ great circle (stereographic distorts distance with ρ — correct using the local scale factor or compute d on the sphere from lat/lon of each sample); interpolated pixels (~90 % of DEM) smooth real terrain; DEM edges truncate view; heights are surface heights, not including boulders.
**Validation.** Synthetic DEMs: flat plane + curvature ⇒ H(α) = −asin(…) pattern; a single known pillar ⇒ known angular width/height; cone ⇒ constant H(α). Compare with Moon Trek line-of-sight/profile tools qualitatively (`UNDER INVESTIGATION` as an external reference).

### 9.2 Solar disk and partial visibility
Sun angular radius $\rho_\odot\approx\arcsin(R_\odot/D)$ with $R_\odot\approx695{,}700$ km, D the Sun distance (≈ 1 AU ⇒ ≈ 0.267°). Fraction of the disk above the horizon at azimuth α can be estimated by integrating the disk area above H(α) (disk vs a locally straight horizon: circular-segment formula). **PROPOSED stages:** (1) centre-of-disk above H; (2) fraction using segment area; (3) full 2-D horizon overlap only if needed. Terrain edge across the disk width is why horizon azimuth resolution must be ≲ a fraction of the disk (≈ ≤ 0.25°).

### 9.3 Illumination windows and events
Sunlit(t) = [el_sun(t) + (partial-disk allowance) > H(az_sun(t))]. Events = sign changes of $f(t)=\text{el}_\odot(t)-H(\text{az}_\odot(t))$ (use disk-upper-limb or centre — **state which**). Find with coarse scan + bisection/Brent (SciPy `brentq`). Durations = differences between event pairs; "time to next sunset" = next downward crossing minus query time.
**Limit.** This is *geometric* line-of-sight to the disk from a point observer on the DEM; it ignores shadows cast by the lander itself, regolith dust, and anything below DEM resolution. Compare with Barker et al. (2021) for a sanity check on illumination fractions (their metric is more sophisticated).

### 9.4 Power potential (optional, `NOT REQUIRED FOR INITIAL IMPLEMENTATION`)
Report **geometric sunlight fraction** and **incidence angle on a stated panel orientation** only:
$\cos\theta_i=\hat s\cdot\hat p$ (panel normal $\hat p$ in ENU), irradiance ∝ $S_0\cos\theta_i$ when $\theta_i<90°$ and Sun visible, with $S_0\approx1361$ W/m² at 1 AU (`Confirmed concept`; Sun–Moon distance varies ±~3 %).
**Never display watts** unless panel area, efficiency, degradation, and orientation are user-supplied inputs; label output "illustrative energy model" in that case.

### 9.5 Earth visibility (geometric)
Same machinery with the Earth direction (disk radius ≈ 0.95°, so partial-visibility handling is more important for Earth than for the Sun). Output: `earth_visible(t)` and windows. **State in every output:** "geometric line-of-sight only; does not include antenna pointing/gain, link budget, ground-station availability, Earth-rotation station coverage, lunar-surface regolith/dust effects, or network scheduling." Do **not** call these "communication windows" without this qualifier.

### 9.6 Time remaining
`time_to_sunset(t)` and `time_to_earthset(t)` from the event list; if no event in the analysed span return `null` plus a `censored: true` flag (not "infinite").

---

## 10. Uncertainty and accuracy

| Source | Size / indicator | Where it comes from | How to carry it |
|---|---|---|---|
| DEM vertical (PGDA) | median RMS Z ~0.30–0.50 m (`VERIFIED`, product 78); mosaic–field residual 30–55 cm (`VERIFIED`, product 81) | `toterr` raster | Report at the site; propagate via clones |
| Slope | median RMS ~1.5–2.5° (`VERIFIED`) | `slperr` raster | Report |
| Interpolation | ~90 % of pixels interpolated; error rises with pole distance & slope (`VERIFIED`) | LDEC count map | Mask/flag low-count areas |
| Frame/registration | 1″ ≈ 8.4 m (calc, §6.5) | DE421 vs chosen kernels | **Must measure** (Phase 4) |
| Ephemeris | Not quantified here (`UNDER INVESTIGATION`) | DE-series documentation | Cite JPL value; compare DE440 vs DE421 |
| Time sampling | step & event tolerance | our config | Convergence test |
| Raster sampling | bilinear vs nearest | our choice | Compare both |

**Sensitivity analysis (`RECOMMENDED`).** For one site: compute horizon and illumination windows with (a) the nominal DEM, (b) at least 10 of the 100 clones (PGDA authors built these precisely to study illumination uncertainty), (c) observer heights 1 m and 5 m (the product page itself notes illumination sensitivity is much smaller at 5 m), and (d) ±pixel/±sub-pixel registration shifts. Report the **spread of event times and window durations** as an interval, labelled "DEM-uncertainty sensitivity," not "probability."

**User-facing reporting (future).** Show windows as nominal with a lighter band for the min–max across clones; list data ids; plain-language caveat. Never show more significant figures than the spread justifies.

---

## 11. Technology evaluation

Rule: **minimal justified set**. Versions are deliberately omitted; pin them from your own working environment (`pip freeze`) after verifying they install together on every teammate's OS.

| Library | What | Needed? | Used in | Learn | Docs | Alternatives / notes |
|---|---|---|---|---|---|---|
| Python | Language | Yes | all | — | <https://docs.python.org/3/> | Pick one version all four can install (verify SpiceyPy/Rasterio wheel availability for it) |
| NumPy | Arrays | **Yes** | all numerics | vectorisation, broadcasting | <https://numpy.org/doc/> | — |
| SpiceyPy | CSPICE wrapper | **Yes** | ephemeris, time | kernels, frames, `spkpos`, `str2et` | <https://spiceypy.readthedocs.io/> | Astropy ephemerides (lower fidelity, less control of frames); Horizons API (online only) |
| Rasterio | Read GeoTIFF + affine | **Yes** | terrain | windows, transforms, nodata | <https://rasterio.readthedocs.io/> | GDAL Python bindings (harder installs), `tifffile` (loses georef) |
| GDAL | C library under Rasterio; `gdalinfo` CLI | Via Rasterio; CLI useful for inspection | data checks | `gdalinfo` | <https://gdal.org/> | — |
| PyProj | Projections | **Optional** — our §6.4 formula is 3 lines and testable; PyProj needs a *custom lunar CRS* definition (the default registry is Earth-centric) | validation | PROJ strings with `+a=… +b=…` | <https://pyproj4.github.io/pyproj/> | Hand-coded sphere formulas + tests |
| SciPy | `map_coordinates`, `brentq`, interpolation | Yes (small use) | terrain, events | — | <https://docs.scipy.org/doc/scipy/> | Pure NumPy interpolation |
| Pydantic | Typed validation/schemas | **Yes** (from API-contract stage) | I/O models | models, validators | <https://docs.pydantic.dev/> | dataclasses + manual checks |
| FastAPI | HTTP layer | **Later** (after schemas stable) | API | routing, OpenAPI | <https://fastapi.tiangolo.com/> | Flask; or none if frontend embeds Python |
| pytest | Tests | **Yes, day 1** | all | fixtures, parametrize | <https://docs.pytest.org/> | unittest |
| Astropy | Units/time/coords | **Optional** (`astropy.units` to avoid unit slips; `Time` for cross-checks) | tests | `Time`, `units` | <https://docs.astropy.org/> | Do not use two time systems in production code |
| Requests/HTTPX | HTTP | Only for Horizons/data download tooling | acquisition | — | <https://www.python-httpx.org/> | `urllib` |
| Pandas | Tables | Optional (event tables) | reporting | — | <https://pandas.pydata.org/docs/> | plain dicts/NumPy |
| Plotly | Plots | **Future** (frontend/reporting) | viz | — | <https://plotly.com/python/> | Matplotlib for validation plots |
| C++ | Speed | **No** until profiling proves Python/NumPy/Numba inadequate | — | — | — | Numba first |

**Environment (`RECOMMENDED`).** One `venv` per developer from a committed `requirements.txt` (loose) and `requirements.lock` (exact, from a known-good machine); `pytest` runs in CI-free mode locally before every PR. Document OS-specific install quirks for Rasterio/SpiceyPy in `docs/SETUP.md` — **test installs on all four machines (Windows/macOS/Linux) before the event**; install failures are a top hackathon time sink.

---

## 12. Backend architecture

**Principle:** pure functions + typed data objects; no module imports a UI; every function takes explicit inputs and returns data plus provenance.

```
selenekto/
  core/          # types, units, constants, errors (no I/O)
  timeconv/      # UTC <-> ET only
  frames/        # lat/lon <-> ENU <-> polar stereographic (pure math)
  ephemeris/     # SPICE wrapper: sun/earth direction in MOON_ME
  terrain/       # DEM loading, tile cropping, interpolation
  horizon/       # H(alpha) profile from a DEM tile
  visibility/    # sun/earth above horizon, partial disk, events
  power/         # (optional) incidence geometry only
  compare/       # scenario runner & ranking
  provenance/    # manifest, checksums, kernel/DEM ids
  validation/    # reference cases, Horizons comparison tools
  api/           # (later) FastAPI + Pydantic schemas
tests/
data/manifest.yaml
```

| Component | Responsibility | Depends on |
|---|---|---|
| `timeconv` | One authoritative UTC↔ET | SPICE LSK |
| `frames` | Coordinate math, ENU, projection | core |
| `ephemeris` | Sun/Earth direction (site-aware, §8) | timeconv, frames, SPICE |
| `terrain` | Read/crop DEM, uncertainty rasters, nodata handling | Rasterio, frames |
| `horizon` | H(α) | terrain, frames |
| `visibility` | Sunlit/Earth-visible series & events | ephemeris, horizon |
| `compare` | Run N scenarios, summarise differences | visibility |
| `provenance` | Attach ids/versions to every result | all |
| `validation` | Reference tests (not imported by production code) | all |

Data flow: `Scenario → (timeconv, ephemeris, terrain→horizon) → visibility → events → Result + provenance`.

---

## 13. Future API contract

**Decision (`RECOMMENDED`):** a REST/JSON API (FastAPI) is appropriate; do **not** choose a frontend framework now. The same Pydantic models serve as the contract. **All examples below are ILLUSTRATIVE — the numbers are placeholders, not calculated results.**

### 13.1 Conventions
- Time: ISO-8601 UTC with `Z`. Angles: degrees. Distances: metres. Longitude: east-positive (−180, 180]. Latitude: planetocentric degrees.
- Azimuth: degrees clockwise from north (0 = N, 90 = E). Elevation: degrees above the *spherical local horizontal*.
- Every result has `meta` (versions, kernels, DEM ids) and `warnings[]`.
- Site IDs: `"pgda:Site01"` for catalogue sites, `"custom:<hash>"` for user coordinates.

### 13.2 Endpoints (proposed)
| Method & path | Purpose |
|---|---|
| `GET /v1/sites` | Catalogue incl. coverage of DEM and uncertainty |
| `POST /v1/analyze` | One scenario → time series, horizon, events |
| `POST /v1/compare` | N scenarios → per-scenario summaries + differences |
| `GET /v1/horizon/{site_id}` | Cached horizon profile |
| `GET /v1/provenance` | Datasets, kernels, versions, checksums |
| `GET /v1/health` | Readiness; offline-capability flags |

### 13.3 Illustrative request
```json
{
  "site": {"id": "pgda:Site01"},
  "observer_height_m": 2.0,
  "time": {"start": "2027-01-01T00:00:00Z", "end": "2027-01-15T00:00:00Z", "step_s": 1800},
  "options": {"disk": "partial", "uncertainty": "clones:10", "event_tolerance_s": 1}
}
```

### 13.4 Illustrative response (placeholders only)
```json
{
  "meta": {
    "time_scale_in": "UTC", "internal": "ET",
    "frame": "MOON_ME", "aberration": "LT+S",
    "dem": {"id": "pgda:Site01", "pixel_m": 5, "sha256": "<recorded>", "interpolated_fraction": "<from LDEC>"},
    "kernels": [{"file": "<name from manifest>", "sha256": "<recorded>"}],
    "software": {"selenekto": "<git commit>"}
  },
  "horizon": {"azimuth_step_deg": 1.0, "elevation_deg": ["<360 values>"], "max_range_m": "<tile-limited>"},
  "series": {"t": ["<ISO>"], "sun": {"az": [], "el": [], "visible_fraction": []},
             "earth": {"az": [], "el": [], "visible_fraction": []}},
  "events": [{"type": "sunset", "t": "<ISO>", "tolerance_s": 1, "uncertainty_band_s": ["<lo>", "<hi>"]}],
  "windows": {"sun": [{"start": "<ISO>", "end": "<ISO>"}], "earth": []},
  "time_to_next": {"sunset_s": null, "earthset_s": null, "censored": true},
  "warnings": ["Earth visibility is geometric only; not a communications link assessment."]
}
```

### 13.5 Errors
`422` schema/validation (with field path); `404` unknown site; `409` site outside DEM coverage; `503` required kernel/dataset missing (with remediation text). Error body: `{"code": "...", "message": "...", "details": {...}}`.

### 13.6 Frontend-readiness gate (all must be true)
1. Core math has passing tests (§17). 2. Output schemas versioned and frozen (`/v1`). 3. Every module has documented I/O. 4. ≥3 reference scenarios with stored expected outputs (from independent checks). 5. Error handling defined. 6. Units/timestamps/provenance in every result. 7. Backend runs headless (CLI/pytest). 8. A small sample dataset lets frontend developers work without GBs. **Migration path:** backend CLI → FastAPI wrapper → frontend consumes OpenAPI; a desktop/mobile client can reuse the same JSON.

---

## 14. Development roadmap

### 14.1 Eleven phases (longer-term plan)

Each phase lists: objective · prerequisites · tasks · tools · deliverables · tests · done-when · common mistakes · depends on.

| # | Phase | Objective & key tasks | Deliverables | Done when | Common mistakes | Depends |
|---|---|---|---|---|---|---|
| 1 | Research | Understand challenge, read §5–§9, compare official challenge text with §4, read rules | Verified §4/§20 | All four can explain Sun/Earth/horizon geometry in 5 min | Skipping rule check; trusting this dossier blindly | — |
| 2 | Data acquisition | Install env; read PGDA README; inspect `Site01` header remotely; download minimal files; fetch generic SPICE kernels; write manifest | `data/manifest.yaml`, `docs/SETUP.md` | `gdalinfo`/Rasterio opens DEM; kernels load in SpiceyPy; checksums stored | Downloading the 3.3 GB mosaic first; losing provenance | 1 |
| 3 | Scientific specification | Freeze conventions of §6–§9 (frame, radius, az definition, time rule) in a short spec | `docs/SPEC.md` (decisions + reasons) | Reviewed by all 4 | Leaving conventions implicit | 1–2 |
| 4 | Reference implementation | Small scripts: UTC→ET; lat/lon↔polar stereo with control points; Sun/Earth az/el; Horizons comparison; **DE421 vs chosen-kernel ME frame offset**; DEM half-pixel check | Notebook/scripts + written findings | Disagreements explained, not hidden | Declaring mismatch before comparing frames/aberration | 2–3 |
| 5 | Backend development | Implement modules of §12 incrementally, tests with each | Modules + tests | Each module has docstrings, tests, one reviewer | Big-bang merges | 3–4 |
| 6 | Integration | Connect modules via typed objects; CLI `selenekto analyze …` | CLI + sample outputs | One scenario runs end-to-end offline | Hidden global state | 5 |
| 7 | Verification | Synthetic terrain, Horizons/SPICE comparison, step-halving, clone sensitivity | Validation report | All tolerances met or documented | Cherry-picked cases | 6 |
| 8 | Comparison engine | N-scenario runner, metrics (e.g. longest continuous sun, overlap of sun & Earth windows) | `compare` + tests | Deterministic ranking with caveats | Ranking without uncertainty | 7 |
| 9 | API & frontend readiness | Pydantic models, FastAPI wrapper, OpenAPI, sample data | Frozen `/v1` | §13.6 gate passes | Changing schema afterwards | 8 |
| 10 | Frontend | Choose framework now; consume API only | UI | Meets §4 requirements 1, 11 | Re-implementing science in JS | 9 |
| 11 | Full validation & demo | End-to-end tests, accessibility check, rehearse talk | Demo, slides, limitations slide | Dry-run passes | Overclaiming | 10 |

Parallelism: Phases 2 (data) and 4 (ephemeris scripts) split between people; terrain and ephemeris tracks meet in Phase 6.

### 14.2 48-hour hackathon plan (`PROPOSED` — the event is 14–15 Nov 2026)

**Before bed tonight (do not skip):** (1) read the official challenge page and rules; (2) all four get `pytest`, NumPy, SpiceyPy, Rasterio installed and importing; (3) download SPICE generic kernels (names from the NAIF directory, *not* this document) and `Site01` surf/toterr rasters; (4) create the repo and a `data/manifest.yaml`.

| Block | Output |
|---|---|
| Sat morning | UTC→ET; Sun & Earth az/el for one lunar site; compare 3 timestamps with Horizons (record frame/aberration used) |
| Sat midday | Open DEM; coordinate transform with ≥3 control points; crop a 20–40 km tile |
| Sat afternoon | Horizon profile H(α) with curvature; synthetic-terrain tests |
| Sat evening | Sunlit/Earth-visible series + sunset/Earthset events for 1 site |
| Sun morning | Compare 2–3 sites/dates; 10-clone sensitivity band if time permits |
| Sun midday | Minimal UI **or** polished notebook/report (frontend is optional under time pressure; correctness + clear story beat a flashy UI) |
| Sun afternoon | README, limitations slide, demo rehearsal, AI-use disclosure |

Cut order if behind: partial-disk → clones → comparison polish → UI; **never cut tests or the limitations slide.**

---

## 15. Team workflow and Git

**Roles (rotate reviewing):**
| Role | Primary | Also learns |
|---|---|---|
| A — Coordinator/Git | repo, CI-less checks, issues, integration, docs | everything's interfaces |
| B — Ephemeris & time | SPICE, `timeconv`, `ephemeris`, Horizons comparison | terrain basics |
| C — Terrain & geospatial | Rasterio, DEM, `frames`, `horizon` | SPICE basics |
| D — Validation & integration | tests, `visibility`, `compare`, provenance | both tracks |

**Rule:** every PR is reviewed by someone from a *different* track and the author must explain it aloud (this builds shared ownership and judge-readiness).

**Git (simple):**
- `main` always passes tests. Work on branches `feature/<short-name>` or `fix/<name>`. No direct pushes to `main`.
- Commits: small, imperative, prefixed `feat:`, `fix:`, `test:`, `docs:`, `data:` (manifest only).
- PR template: *what/why, how tested, scientific assumptions touched, AI assistance used (yes/no, where).*
- Merge: squash-merge after one review + green `pytest`.
- Conflicts: pull `main` into your branch daily; resolve locally; ask A if unsure; never force-push shared branches.
- Issues: GitHub Issues with labels `science`, `data`, `bug`, `docs`; one issue per task.
- Learning Git: A runs a 30-minute pair session (clone → branch → commit → push → PR → review → merge) using a throwaway repo; resources in §16.

---

## 16. Learning programme

### 16.1 Essential before backend work
| Topic | Learn | Why | Free resources | You can explain afterwards |
|---|---|---|---|---|
| Lunar sky & libration | Tidal locking, libration, why the pole has near-horizon Sun | Sanity checks | NASA LRO/LROC and Artemis pages; Barker et al. (2021) intro | Why Sun elevation at the pole is within ~1.5° |
| Coordinates | lat/lon, ENU, projections | §6 | PROJ docs (<https://proj.org/>), Snyder, *Map Projections — A Working Manual* (USGS) | Derive el/az from a vector |
| Ephemeris & SPICE basics | Kernels, frames, time | §5, §7 | NAIF tutorials/lessons (<https://naif.jpl.nasa.gov/naif/tutorials.html>) | Why `LT+S`, what `furnsh` does |
| Python scientific | NumPy vectorisation | All | NumPy "absolute beginners" docs | Replace a loop with array ops |
| Raster basics | Affine transform, nodata, windows | §6.6 | Rasterio docs; GDAL docs | Pixel centre vs corner |
| Git collaboration | Branch/PR/review | §15 | Pro Git book (free, <https://git-scm.com/book>) | Make a PR |
| Numerical testing | tolerances, reference cases | §17 | pytest docs | Why `approx(rel=…)` not `==` |

### 16.2 During backend development
SpiceyPy API; DEM interpolation; local tangent frames; horizon algorithm (ray marching); event root-finding (SciPy `brentq`); Pydantic/FastAPI tutorials (official docs).

### 16.3 Advanced/optional
Uncertainty propagation (Monte Carlo over clones); solar power modelling; RF link budgets; ray tracing (Barker et al. discuss illumination modelling); Numba/C++ optimisation; other datasets (PDS LRO instruments).

---

## 17. Testing and validation

### 17.1 Principles
Tests describe *physical or mathematical truth*, not "what the code printed last time." Every test records its source of truth.

### 17.2 Test catalogue
| Layer | Tests |
|---|---|
| Unit | `timeconv` known epochs (J2000 ⇒ ET 0 for 2000-01-01T12:00:00 **TDB**; UTC offset ≈ 64.184 s — *confirm against SPICE*); leap-second boundaries |
| Coordinates | lat/lon↔(x,y) round-trip; pole ⇒ (0,0); control points from PGDA (read from DEM/README, not invented) |
| Geometry | Body at zenith ⇒ el = 90°; body along +east ⇒ az = 90°; horizon-plane vector ⇒ el = 0 |
| Ephemeris | SPICE vs Horizons at several epochs (§17.3); sub-Earth point ⇒ Earth near zenith |
| Terrain/DEM | metadata checks: CRS present, 5 m pixel, nodata, `AREA_OR_POINT`, expected extent |
| Synthetic terrain | flat+curvature; single pillar; ridge; cone; symmetric bowl ⇒ symmetric H(α) |
| Horizon | compare numeric H(α) with analytic expectation for synthetic cases |
| Visibility | step function Sun elevation crossing a constant horizon ⇒ exact event time (bisection tolerance) |
| Temporal | halve time step ⇒ events move < tolerance |
| Comparison | swapping scenario order doesn't change per-scenario results |
| Offline | run full scenario with network disabled and all data local |
| Integration | CLI end-to-end on the small sample |

### 17.3 Comparing SPICE with Horizons — checklist (do all before calling anything "wrong")
Same epoch and time scale (UTC vs TDB); same target and center; same **body-fixed frame** (ME vs PA) and **site definition** (Horizons E-longitude, geodetic vs planetocentric, height reference); same **aberration/light-time** (airless apparent vs geometric); same **ephemeris version** (DE number); same angular-unit/rounding; Horizons header text recorded in the test. Store a few Horizons outputs as fixtures with the exact request.

### 17.4 Reproducible reference cases
Each case = scenario JSON + expected output + provenance of expected values (Horizons query, analytic derivation, or published paper) + tolerance and why. Store under `tests/reference/`.

### 17.5 Never-do list
Hard-coded leap-second counts, comparing floating-point times with `==`, using the tests to freeze buggy output, using only one site.

---

## 18. Offline/online operation

`RECOMMENDED` design: an *acquisition* tool (separate, online) downloads and checksums datasets into `data/raw/` and updates the manifest; the *calculation core* never touches the network and fails with a clear error if a kernel/DEM is missing. SPICE kernels and DEMs are local files; verify SHA-256 on load (or at startup). Horizons is used **only** in `validation/` with cached fixtures. External-service outage ⇒ production path unaffected. **Do not advertise offline capability until the "offline" test (§17.2) passes on a clean machine.** Version datasets by manifest id; a result's `meta` must let anyone re-fetch exact inputs.

---

## 19. Risk register

| # | Risk | L | I | Mitigation | Verification |
|---|---|---|---|---|---|
| 1 | Wrong coordinate transform (axis orientation, k₀, radius) | M | H | Control-point tests; hand-checked formula | §17.2 coordinates |
| 2 | Frame mismatch DEM(ME, DE421) vs ephemeris frame | H | H | Quantify in Phase 4; use consistent kernels | Frame-offset report |
| 3 | Ephemeris version mismatch | M | M | Record kernel ids; compare DE421/DE440 | Manifest + test |
| 4 | Time-conversion errors | M | H | Single module; LSK from kernel | Epoch tests |
| 5 | DEM resolution/interpolation limits (~90 % interpolated) | H | M | Clones, flags, observer heights | Sensitivity run |
| 6 | Terrain uncertainty ignored | M | H | Report bands | Output includes interval |
| 7 | Nodata/edge truncation | M | M | Mask, report $d_{max}$ | Edge tests |
| 8 | Huge files (3.3–4.9 GB) | H | M | Sites first; windowed reads; crops | Disk/RAM check |
| 9 | Coverage gaps (custom coordinates outside DEM) | M | M | 409 error + message | API test |
| 10 | Claiming power output | M | H | Geometric only unless hardware given | Label review |
| 11 | Claiming comms feasibility | M | H | Always include caveat string | Output schema test |
| 12 | Unvalidated sampling | M | M | Step-halving | Convergence test |
| 13 | Insufficient testing | H | H | Tests per PR | Review rule |
| 14 | Overengineering | M | M | MVSP scope (§3.1) | Scope review |
| 15 | Not enough time (hackathon ≤ 48 h) | **H** | H | §14.2 cut order | Checkpoints |
| 16 | Install failures across OS | M | M | Pre-event install test | Everyone imports libs |
| 17 | Misread challenge/rules | M | H | Verify against official page | §4/§20 |

---

## 20. Verification debt and unresolved questions

1. **Official challenge text and judging criteria** — page was robots-blocked; compare with §4.
2. **Submission deadlines, eligibility, AI-use disclosure rules** — not read.
3. **Exact current SPICE generic kernel files** (LSK, planetary SPK, lunar PCK, FK) — directory not fetched; record names, dates, sizes.
4. **DE421 vs DE440 ME-frame difference** — unquantified.
5. **PGDA README** (projection parameters k₀/λ₀, radius, data type, nodata) — not read.
6. **Per-site file sizes** (e.g. Site01) and licence/attribution terms — not verified.
7. **Horizons lunar-site syntax** (`coord@301`?) and frame conventions — untested.
8. **PDS LOLA product identifiers/releases** and whether better/newer DEMs exist — not investigated.
9. **QuickMap/Moon Trek** export/line-of-sight capabilities and account requirements — not tested.
10. **Package install/compat on team OSes** — not tested.
11. **Existing GitHub repo** — not accessible; nothing inspected, nothing committed.

---

## 21. Judging and presentation strategy

Strongest evidence to *build and show*: (1) a validated Sun/Earth az/el vs Horizons table; (2) horizon profile from real LOLA terrain, with and without terrain, showing a case where terrain changes the answer; (3) a two- or three-site comparison with uncertainty bands; (4) explicit limitations slide. Avoid: unvalidated power numbers, "communication window" wording, decorative 3-D graphics. Storytelling: a planner asks a question → SelenEkto answers → here's how we know it's right → here's what it can't tell you.

---

## 22. Human ownership and AI policy

The team owns the project; AI is a support tool. Read the competition's *current* AI rules and disclose AI assistance as required (this dossier itself was AI-drafted and **must be reviewed and corrected by the team**). Each PR records AI help. No AI/ML in the product unless the team justifies it. Everyone must be able to derive el/az, describe the horizon algorithm and explain each validation, without notes.

---

## 23. Final actionable checklist

- [ ] Read official challenge page and rules; update §4/§20
- [ ] Create repo, `.gitignore` (data/raw), branch rules, issue labels
- [ ] Everyone: venv + NumPy, SpiceyPy, Rasterio, pytest import OK
- [ ] Download SPICE generic kernels; record in manifest
- [ ] Read PGDA README; download `Site01` surf + toterr; checksum
- [ ] UTC→ET and Sun/Earth az/el scripts; 3 Horizons comparisons
- [ ] Coordinate transform with control points; half-pixel check
- [ ] Quantify DE421/chosen-kernel frame offset
- [ ] Horizon module + synthetic tests
- [ ] Visibility events + step-halving test
- [ ] Compare ≥2 scenarios; uncertainty band (if time)
- [ ] Limitations slide; AI-use disclosure; demo rehearsal

---

## 24. Glossary

**Azimuth** — compass direction of a body, 0° north, clockwise. **CK/FK/LSK/PCK/SCLK/SPK** — SPICE kernel types (orientation/frames/leap seconds/planetary constants/clock/ephemeris). **DEM/LDEM** — digital elevation model. **ET** — SPICE ephemeris time. **GeoTIFF** — TIFF with georeferencing. **LDEC** — LOLA count map. **LOLA/LRO** — Lunar Orbiter Laser Altimeter / Lunar Reconnaissance Orbiter. **ME / PA** — Mean Earth/polar axis; principal axes frames. **ENU** — East-North-Up local frame. **Libration** — apparent wobble of the Moon seen from Earth. **TDB/TT/UTC** — time scales. **XYZI** — point cloud (x, y, z, intensity).

---

## 25. References

Accessed 2026-11-13 unless noted. `VERIFIED` = text read this session.

1. NASA Science — Space Apps 2026 registration/dates: <https://science.nasa.gov/universe/nasa-welcomes-all-ages-experience-levels-for-space-apps-challenge/> (VERIFIED snippet)
2. Astronet — event dates 14–15 Nov 2026: <https://astronet.pl/wydarzenia/nasa-space-apps-challenge-2026-juz-w-listopadzie-zapisy-trwaja/> (VERIFIED)
3. The Recursive — 14–15 Nov: <https://www.therecursive.com/nasa-space-apps-challenge-2026-where-to-join-it-in-cee/> (VERIFIED)
4. Official challenge page (UNAVAILABLE to tool): <https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/>
5. PGDA product 78: <https://pgda.gsfc.nasa.gov/products/78> (VERIFIED)
6. PGDA product 81: <https://pgda.gsfc.nasa.gov/products/81> (VERIFIED)
7. PGDA data root / README: <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/> · <https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/README> (listed; README not read)
8. Barker et al. (2021), PSS 203, 105119: <https://doi.org/10.1016/j.pss.2020.105119> (cited by PGDA; paper not read)
9. Mazarico et al. (2011) site numbering — cited by PGDA; not read
10. NAIF lunar data listing: <https://naif.jpl.nasa.gov/naif/data_lunar.html> (VERIFIED)
11. NAIF home: <https://naif.jpl.nasa.gov/> · generic kernels: <https://naif.jpl.nasa.gov/pub/naif/generic_kernels/> (not fetched)
12. Horizons API doc: <https://ssd-api.jpl.nasa.gov/doc/horizons.html> (VERIFIED snippet) · Horizons manual: <https://ssd.jpl.nasa.gov/horizons/manual.html> (not fetched)
13. SpiceyPy: <https://spiceypy.readthedocs.io/>
14. Rasterio <https://rasterio.readthedocs.io/> · GDAL <https://gdal.org/> · PyProj <https://pyproj4.github.io/pyproj/> · NumPy <https://numpy.org/doc/> · SciPy <https://docs.scipy.org/doc/scipy/> · Pydantic <https://docs.pydantic.dev/> · FastAPI <https://fastapi.tiangolo.com/> · pytest <https://docs.pytest.org/> · Astropy <https://docs.astropy.org/> · Plotly <https://plotly.com/python/>
15. Archives/platforms (not fetched): <https://pds.nasa.gov/> · <https://pds-geosciences.wustl.edu/missions/lro/> · <https://imbrium.mit.edu/> · <https://quickmap.lroc.asu.edu/> · <https://trek.nasa.gov/moon/> · <https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/>

*End of dossier v0.1.*
