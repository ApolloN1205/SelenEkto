"""Read and validate the SelenEkto lunar location catalogue."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from .paths import project_root


class CatalogueError(ValueError):
    """Raised when the location catalogue is incomplete or inconsistent."""


def load_catalog(root: Path | None = None) -> dict[str, Any]:
    base = root or project_root()
    path = base / "data/catalog/landing_sites.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CatalogueError(f"Missing location catalogue: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CatalogueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(payload.get("sites"), list):
        raise CatalogueError("Catalogue must contain a 'sites' array")
    return payload


def validate_catalog(root: Path | None = None) -> list[str]:
    payload = load_catalog(root)
    issues: list[str] = []
    seen_ids: set[str] = set()
    for index, site in enumerate(payload["sites"]):
        prefix = f"sites[{index}]"
        site_id = site.get("id")
        if not site_id:
            issues.append(f"{prefix}: missing id")
        elif site_id in seen_ids:
            issues.append(f"{prefix}: duplicate id {site_id}")
        else:
            seen_ids.add(site_id)
        for field, low, high in (("latitude_deg", -90.0, 90.0), ("longitude_deg", -180.0, 180.0)):
            value = site.get(field)
            if not isinstance(value, (int, float)) or not low <= value <= high:
                issues.append(f"{prefix}: {field} must be numeric in [{low}, {high}]")
        if site.get("coordinate_role") != "representative_region_centre":
            issues.append(f"{prefix}: coordinate_role must be representative_region_centre")
        if not site.get("coordinate_source", {}).get("url"):
            issues.append(f"{prefix}: missing coordinate source URL")
        if site.get("elevation_km") is None:
            # Missing altitude is deliberate; a location centre is not a DEM surface sample.
            pass
    return issues


def list_sites(root: Path | None = None) -> list[dict[str, Any]]:
    return load_catalog(root)["sites"]


def get_site(identifier: str, root: Path | None = None) -> dict[str, Any]:
    key = identifier.strip().casefold()
    for site in list_sites(root):
        aliases = {site["id"], site["name"], site["short_name"], *site.get("other_shorthands", [])}
        if key in {str(alias).casefold() for alias in aliases}:
            return site
    raise KeyError(f"Unknown SelenEkto lunar site: {identifier}")


def export_csv(root: Path | None = None) -> Path:
    base = root or project_root()
    sites = list_sites(base)
    output = base / "data/catalog/landing_sites.csv"
    fields = ["id", "name", "short_name", "latitude_deg", "longitude_as_published_deg",
              "coordinate_role", "coordinate_frame", "coordinate_source_document",
              "coordinate_source_table", "coordinate_source_page"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for site in sites:
            writer.writerow({
                "id": site["id"], "name": site["name"], "short_name": site["short_name"],
                "latitude_deg": site["latitude_deg"],
                "longitude_as_published_deg": site["longitude_as_published_deg"],
                "coordinate_role": site["coordinate_role"], "coordinate_frame": site["coordinate_frame"],
                "coordinate_source_document": "M2M-30044", "coordinate_source_table": "A2.1-1",
                "coordinate_source_page": 75,
            })
    return output
