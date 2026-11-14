# SelenEkto — Site01 DEM-limited horizon prototype

This add-on creates a **terrain-only** horizon scan around the published Site01 (Connecting Ridge) representative region centre. It does not compute Sun position, illumination, or landing safety.

## Install into the existing infrastructure

Copy the add-on's `src/selenekto_data/horizon.py`, `scripts/horizon_site01.py`, and `tests/test_horizon.py` into the corresponding directories under your existing **outer** `SelenEkto_Data_Infrastructure` folder. Keep all your existing files. Do not copy this package as another nested `SelenEkto_Data_Infrastructure`.

From PowerShell in the outer infrastructure directory:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
.\.venv\Scripts\python.exe .\scripts\horizon_site01.py
```

Expected output locations (ignored processed data):

- `data/processed/horizon/Site01/Site01_horizon.json`
- `data/processed/horizon/Site01/Site01_horizon.png`

Optional experiment (e.g. observation height 2 metres and scan radius 6 km):

```powershell
.\.venv\Scripts\python.exe .\scripts\horizon_site01.py --observer-height-m 2 --max-distance-m 6000
```

**Warning:** Rerunning overwrites the same generated JSON and PNG. The settings are recorded in the JSON.

## How it works

A ray is cast for each **grid-relative** azimuth (default every 1 degree). Terrain is sampled at 10-metre intervals up to 5 km. For each sample, the code computes the apparent elevation angle to the sample while allowing for Moon curvature. The maximum sampled apparent angle becomes the DEM-limited horizon direction.

Angle formula: let R be lunar reference radius, z0 observer DEM elevation, h eye height, zt target elevation, and d approximately the surface distance. Set a=d/R, rt=R+zt, ro=R+z0+h. Then angle = atan2(rt cos(a)-ro, rt sin(a)).

**Direction caveat:** 0° means +Y in the *projected GeoTIFF grid*, 90° means +X. These are **not necessarily lunar true north/east**. Don't overlay the angles on a geographic compass or use them with Sun azimuth until a correct lunar coordinate-frame transformation has been validated.

**Distance caveat:** these projected sample distances are used as approximations of lunar surface arc distances. Datum/elevation radius interpretation should be independently checked for serious scientific use.

**Grid coverage caveat:** only this 16-km-wide Site01 raster is searched. It cannot rule out farther terrain. Even with 360 directions and zero edge truncations, **this is not a global physical horizon**. LOS/illumination will require mosaic coverage and a separate verified solar ephemeris model.

**Data integrity:** The DEM contains many interpolated cells. The code carries through the contributing raster cell's LOLA return count and reported elevation RMS uncertainty, but DOES NOT propagate the uncertainty into the angle. `controlling_measurement_count = 0` is an important scientific-quality warning.

**Sampling:** nearest-pixel ray sampling may miss small narrow obstacles; finer distance/angle steps improve sampling but not raster resolution. Use all results as prototype estimates.

## Next engineering steps

1. Validate projection-to-geographic azimuth transformation and DEM radial datum.
2. Improve sampling for features missed by centreline rays.
3. Add uncertainty sensitivity / ensemble DEM clones.
4. Extend horizon to sufficiently broad terrain coverage.
5. Only then combine horizon with Sun elevations at specific dates/times.

## Reference data

NASA/GSFC PGDA LOLA 5 m/pixel South Pole Landing Site DEMs: https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/
Barker et al. (2021), *Improved LOLA Elevation Maps for South Pole Landing Sites: Error Estimates and Their Impact on Illumination Conditions*.
