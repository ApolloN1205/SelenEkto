"""Repository path helpers shared by the data tools."""
from __future__ import annotations

import os
from pathlib import Path


def project_root(start: Path | None = None) -> Path:
    """Find a SelenEkto root containing data/catalog/landing_sites.json.

    SELENEKTO_ROOT may be set when running outside the repository root.
    """
    configured = os.environ.get("SELENEKTO_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if (root / "data/catalog/landing_sites.json").is_file():
            return root
        raise FileNotFoundError(
            f"SELENEKTO_ROOT={root} does not contain data/catalog/landing_sites.json"
        )

    here = (start or Path.cwd()).resolve()
    candidates = [here, *here.parents]
    for candidate in candidates:
        if (candidate / "data/catalog/landing_sites.json").is_file():
            return candidate
    # When this package is installed from the standalone selenekto_data_layer folder,
    # its package root is a valid default data root even when called from the app root.
    packaged_root = Path(__file__).resolve().parents[2]
    if (packaged_root / "data/catalog/landing_sites.json").is_file():
        return packaged_root
    raise FileNotFoundError(
        "Could not find the SelenEkto data catalogue. Run from the data-layer folder, "
        "set SELENEKTO_ROOT to that folder, or install the package in the existing repo." 
    )
