"""Read the machine-readable dataset and source registries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .paths import project_root


def load_dataset_registry(root: Path | None = None) -> dict[str, Any]:
    base = root or project_root()
    return json.loads((base / "data/manifests/datasets.json").read_text(encoding="utf-8"))


def list_datasets(root: Path | None = None) -> list[dict[str, Any]]:
    return load_dataset_registry(root)["datasets"]


def find_dataset(dataset_id: str, root: Path | None = None) -> dict[str, Any]:
    key = dataset_id.casefold()
    for item in list_datasets(root):
        if item["dataset_id"].casefold() == key:
            return item
    raise KeyError(f"Unknown dataset ID: {dataset_id}")


def datasets_for_site(site_code: str, root: Path | None = None) -> list[dict[str, Any]]:
    key = site_code.casefold()
    return [d for d in list_datasets(root) if d["site_code"].casefold() == key]


def find_by_site_and_kind(site_code: str, kind: str, root: Path | None = None) -> dict[str, Any]:
    matches = [d for d in datasets_for_site(site_code, root) if d["dataset_id"].casefold().endswith("_" + kind.casefold())]
    if len(matches) != 1:
        raise KeyError(f"Expected one {kind} product for {site_code}; found {len(matches)}")
    return matches[0]
