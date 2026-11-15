"""Build a reusable SelenEkto terrain profile for a registered PGDA site."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Support running this script from the data-layer folder before editable install.
PACKAGE_SRC = Path(__file__).resolve().parents[1] / "src"
if PACKAGE_SRC.is_dir() and str(PACKAGE_SRC) not in sys.path:
    sys.path.insert(0, str(PACKAGE_SRC))

from selenekto_data.terrain import analyze_site  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a verified SelenEkto terrain profile")
    parser.add_argument("--site", required=True, help="PGDA site code, e.g. Site01")
    parser.add_argument("--output-dir", default="data/processed/site_profiles")
    parser.add_argument("--root", default=None, help="Optional data-layer root")
    args = parser.parse_args()

    try:
        report = analyze_site(args.site, root=args.root, output_dir=args.output_dir)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(f"Created terrain profile for {args.site} ({report.get('region_name')}).")
    print("Verified layers:")
    for key, layer in report["layers"].items():
        stats = layer["statistics"]
        print(
            f"  {key:<24} {stats['valid_pixels']:,}/{stats['total_pixels']:,} valid; "
            f"range {stats['minimum']:.4f} to {stats['maximum']:.4f} {layer['unit_from_product_documentation']}"
        )
    print(f"Output: {args.output_dir}\\{args.site}_terrain_profile.json")
    print("No horizon, illumination, or communications result has been calculated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
