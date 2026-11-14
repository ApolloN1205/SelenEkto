"""JPL Horizons observer-table client for Sun/Earth directions from lunar sites.

Uses Horizons observer quantity 4 (apparent azimuth/elevation). Per JPL's manual,
refraction is not modelled for non-Earth sites. This is a celestial direction relative
to Horizons' local horizon convention; terrain obstruction must be modelled separately.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import project_root

API_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
TARGET_CODES = {"sun": "10", "earth": "399"}


class HorizonsError(RuntimeError):
    pass


def signed_east_to_0_360(longitude_east_deg: float) -> float:
    """Normalize a *confirmed east-positive* lunar longitude to [0, 360)."""
    if not -360.0 <= longitude_east_deg <= 360.0:
        raise ValueError("Longitude must be between -360 and 360 degrees")
    return longitude_east_deg % 360.0


def _numbers_from_fields(fields: list[str]) -> list[float]:
    values: list[float] = []
    numeric = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[Ee][-+]?\d+)?")
    for field in fields:
        for token in numeric.findall(field):
            try:
                values.append(float(token))
            except ValueError:
                continue
    return values


def parse_observer_result(result_text: str) -> list[dict[str, Any]]:
    """Parse the CSV data between Horizons $$SOE and $$EOE markers.

    The parser intentionally preserves the original row and date tag. It expects the
    first two numeric fields after the time tag to be apparent azimuth and elevation
    for QUANTITIES=4, and raises instead of guessing if that shape is absent.
    """
    start = result_text.find("$$SOE")
    end = result_text.find("$$EOE")
    if start < 0 or end < 0 or end <= start:
        raise HorizonsError("Horizons response did not contain $$SOE / $$EOE data markers")
    data_block = result_text[start + len("$$SOE"):end]
    rows: list[dict[str, Any]] = []
    for raw_line in data_block.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = next(csv.reader([line], skipinitialspace=True))
        if len(fields) < 2:
            continue
        time_tag = fields[0].strip()
        numbers = _numbers_from_fields(fields[1:])
        if len(numbers) < 2:
            # Header/annotation lines are not data rows; only fail if the line resembles a date row.
            if re.search(r"\d{4}[-A-Za-z]", time_tag):
                raise HorizonsError(f"Could not parse AZ/EL from Horizons row: {line}")
            continue
        azimuth, elevation = numbers[0], numbers[1]
        if not 0.0 <= azimuth <= 360.0 or not -90.0 <= elevation <= 90.0:
            raise HorizonsError(f"Parsed AZ/EL outside expected angular ranges: {line}")
        rows.append({
            "time_tag": time_tag,
            "azimuth_deg": azimuth,
            "elevation_deg": elevation,
            "quantity_interpretation": "Horizons observer quantity 4: apparent azimuth/elevation",
            "raw_csv_row": line,
        })
    if not rows:
        raise HorizonsError("No ephemeris rows could be parsed from Horizons response")
    return rows


def build_query_params(*, target: str, longitude_east_deg: float, latitude_deg: float,
                       altitude_km: float, start_time_utc: str, stop_time_utc: str,
                       step_size: str = "10m") -> dict[str, str]:
    target_key = target.strip().casefold()
    if target_key not in TARGET_CODES:
        raise ValueError("target must be 'sun' or 'earth'")
    if not -90 <= latitude_deg <= 90:
        raise ValueError("latitude_deg must be between -90 and 90")
    if not 0 <= longitude_east_deg < 360:
        raise ValueError("longitude_east_deg must be in [0, 360); explicitly normalize source longitude first")
    if altitude_km < -10 or altitude_km > 100:
        raise ValueError("altitude_km outside conservative supported range")
    # Validate timestamps; Horizons accepts date/time strings. Require UTC-labelled values.
    for label, value in (("start_time_utc", start_time_utc), ("stop_time_utc", stop_time_utc)):
        if not value.endswith("Z"):
            raise ValueError(f"{label} must end in Z to make UTC explicit")
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    start = datetime.fromisoformat(start_time_utc.replace("Z", "+00:00"))
    stop = datetime.fromisoformat(stop_time_utc.replace("Z", "+00:00"))
    if stop <= start:
        raise ValueError("stop_time_utc must be later than start_time_utc")
    if not re.fullmatch(r"\d+\s*(?:m|min|h|d|s)", step_size.strip(), re.IGNORECASE):
        raise ValueError("step_size must resemble '10m', '1h' or '1d'")
    return {
        "format": "json",
        "COMMAND": TARGET_CODES[target_key],
        "OBJ_DATA": "NO",
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@301",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": f"{longitude_east_deg:.8f},{latitude_deg:.8f},{altitude_km:.6f}",
        "START_TIME": start_time_utc.replace("T", " ").replace("Z", ""),
        "STOP_TIME": stop_time_utc.replace("T", " ").replace("Z", ""),
        "STEP_SIZE": step_size,
        "QUANTITIES": "4",
        "CSV_FORMAT": "YES",
        "TIME_TYPE": "UT",
        "TIME_DIGITS": "SECONDS",
    }


def query_horizons(*, target: str, longitude_east_deg: float, latitude_deg: float,
                   start_time_utc: str, stop_time_utc: str, altitude_km: float = 0.0,
                   step_size: str = "10m", root: Path | None = None,
                   timeout: int = 40, use_cache: bool = True) -> dict[str, Any]:
    """Query Horizons and cache the raw response and parsed direction rows.

    Important: longitude_east_deg must be an east-positive Moon ME longitude compatible
    with Horizons. Do not pass a source value until its longitude convention is confirmed.
    """
    params = build_query_params(target=target, longitude_east_deg=longitude_east_deg,
                                latitude_deg=latitude_deg, altitude_km=altitude_km,
                                start_time_utc=start_time_utc, stop_time_utc=stop_time_utc,
                                step_size=step_size)
    base = root or project_root()
    cache_dir = base / "data/cache/horizons"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()
    cache_path = cache_dir / f"{cache_key}.json"
    if use_cache and cache_path.is_file():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["cache_hit"] = True
        return payload

    url = API_URL + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "SelenEkto/0.1 (student research project)", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            status = getattr(response, "status", response.getcode())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HorizonsError(f"Could not reach JPL Horizons: {exc}") from exc
    if status != 200:
        raise HorizonsError(f"JPL Horizons returned HTTP {status}")
    try:
        body = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HorizonsError("JPL Horizons returned non-JSON or invalid JSON") from exc
    if body.get("error"):
        raise HorizonsError(f"JPL Horizons error: {body['error']}")
    result_text = body.get("result")
    if not isinstance(result_text, str):
        raise HorizonsError("JPL Horizons JSON did not include a result string")
    rows = parse_observer_result(result_text)
    output = {
        "provider": "NASA/JPL Horizons API",
        "provider_url": API_URL,
        "query_parameters": params,
        "target": target.casefold(),
        "observer": "user-defined lunar surface site on Moon (301)",
        "coordinate_convention": "GEODETIC; east longitude degrees, latitude degrees, altitude km; Moon ME/DE421 convention per JPL manual",
        "quantity": "4 (apparent azimuth/elevation)",
        "refraction_note": "JPL states refraction is not modelled for non-Earth observers; terrain obstruction is not included in these angles.",
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "http_status": status,
        "rows": rows,
        "raw_result": result_text,
        "cache_hit": False,
    }
    cache_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    return output
