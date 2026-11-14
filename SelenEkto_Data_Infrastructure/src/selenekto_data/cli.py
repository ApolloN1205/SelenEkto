"""Command-line interface: python -m selenekto_data <command>."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .catalog import export_csv, get_site, list_sites, validate_catalog
from .download import DEFAULT_MAX_BYTES, DownloadError, download_dataset
from .horizons import HorizonsError, query_horizons, signed_east_to_0_360
from .paths import project_root
from .registry import datasets_for_site, find_by_site_and_kind, find_dataset, list_datasets
from .validation import inspect_raster, validate_registry


def _root_from_args(args: argparse.Namespace) -> Path:
    return Path(args.root).resolve() if getattr(args, "root", None) else project_root()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="selenekto-data", description="SelenEkto scientific data tools")
    parser.add_argument("--root", help="Repository root (defaults to auto-detection)")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List the 13 Artemis candidate-region reference points")
    sub.add_parser("products", help="List PGDA registered download products")
    sub.add_parser("status", help="Show acquisition status for registered products")
    sub.add_parser("validate", help="Validate site catalogue, registry and local files")
    sub.add_parser("build-catalog", help="Regenerate the human-readable CSV location catalogue")

    fetch = sub.add_parser("fetch", help="Download an officially listed PGDA product")
    fetch.add_argument("--site", required=True, help="PGDA site code, e.g. Site01")
    fetch.add_argument("--kind", required=True,
                       choices=["ldem", "xyzi", "ldec", "slope", "total_z_uncertainty", "slope_uncertainty", "all"])
    fetch.add_argument("--max-mb", type=float, default=500.0,
                       help="Maximum size per file in MiB (default 500; raise explicitly only after review)")
    fetch.add_argument("--timeout", type=int, default=45)

    raster = sub.add_parser("inspect-raster", help="Read-only inspection of a local GeoTIFF")
    raster.add_argument("path", help="Path to a raster file")

    horizon = sub.add_parser("horizons", help="Query JPL Horizons for lunar-observer Sun/Earth AZ/EL")
    horizon.add_argument("--target", required=True, choices=["sun", "earth"])
    horizon.add_argument("--latitude-deg", type=float, required=True)
    horizon.add_argument("--longitude-east-deg", type=float, required=True,
                         help="East-positive longitude in [0,360), confirmed for the source coordinate frame")
    horizon.add_argument("--altitude-km", type=float, default=0.0)
    horizon.add_argument("--start", required=True, help="UTC ISO timestamp e.g. 2026-11-14T00:00:00Z")
    horizon.add_argument("--stop", required=True, help="UTC ISO timestamp later than --start")
    horizon.add_argument("--step", default="10m")
    horizon.add_argument("--no-cache", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        root = _root_from_args(args)
        if args.command == "list":
            for site in list_sites(root):
                print(f"{site['id']:<30} {site['name']:<32} {site['latitude_deg']:>9.4f}, {site['longitude_as_published_deg']:>10.5f}  [{site['short_name']}]")
            return 0

        if args.command == "products":
            for item in list_datasets(root):
                print(f"{item['dataset_id']:<36} {item['site_code']:<8} {item['product_type']:<24} {item['acquisition_status']}")
            print(f"\n{len(list_datasets(root))} product records; binary files are not bundled.")
            return 0

        if args.command == "status":
            records = list_datasets(root)
            downloaded = 0
            for item in records:
                path = root / item["local_path"]
                present = path.is_file()
                if present:
                    downloaded += 1
                print(f"{'PRESENT' if present else 'MISSING':<8} {item['dataset_id']:<36} {path.stat().st_size if present else '-'}")
            print(f"\n{downloaded}/{len(records)} registered files present locally.")
            return 0

        if args.command == "validate":
            issues = validate_registry(root)
            if issues:
                print("VALIDATION ISSUES:")
                for issue in issues:
                    print(f"- {issue}")
                return 1
            print("Catalogue and registry checks passed. Downloaded files are checked against recorded size and SHA-256.")
            print("This does not prove scientific suitability; inspect actual raster metadata and product documentation.")
            return 0

        if args.command == "build-catalog":
            output = export_csv(root)
            print(f"Wrote {output.relative_to(root)}")
            return 0

        if args.command == "fetch":
            if args.kind == "all":
                selected = datasets_for_site(args.site, root)
            else:
                selected = [find_by_site_and_kind(args.site, args.kind, root)]
            if not selected:
                raise KeyError(f"No explicitly registered products found for {args.site}")
            max_bytes = int(args.max_mb * 1024 * 1024)
            for item in selected:
                print(f"Downloading {item['dataset_id']} from {item['download_url']}")
                result = download_dataset(item, root, max_bytes=max_bytes, timeout=args.timeout)
                print(json.dumps(result, indent=2))
            return 0

        if args.command == "inspect-raster":
            path = Path(args.path)
            if not path.is_absolute():
                path = root / path
            print(json.dumps(inspect_raster(path), indent=2))
            return 0

        if args.command == "horizons":
            result = query_horizons(
                target=args.target, longitude_east_deg=args.longitude_east_deg,
                latitude_deg=args.latitude_deg, altitude_km=args.altitude_km,
                start_time_utc=args.start, stop_time_utc=args.stop,
                step_size=args.step, root=root, use_cache=not args.no_cache,
            )
            print(json.dumps({k: v for k, v in result.items() if k != "raw_result"}, indent=2))
            return 0

    except (FileNotFoundError, KeyError, ValueError, DownloadError, HorizonsError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
