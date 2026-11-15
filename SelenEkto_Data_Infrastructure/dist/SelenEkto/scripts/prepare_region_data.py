"""Enrich every installed region profile with human-readable measurements."""
from __future__ import annotations
import argparse
import csv
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from selenekto_v2.region_data import prepare_profiles, load_profiles, METRIC_COLUMNS, metric_value

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--profile-dir', type=Path, default=ROOT/'data/catalog/region_profiles')
    args = parser.parse_args()
    results = prepare_profiles(args.profile_dir)
    if not results:
        raise SystemExit('No region profile JSON files found. First run scripts/build_all_region_json.py from the infrastructure folder.')
    print('SELENEKTO / REGION PROFILE SUMMARY')
    for r in results:
        print(f"{r['region']:<12} {r['status']:<26} {r['ready_layers']}/5 layers" +
              (f" | {r['errors'][0]}" if r['errors'] else ''))
    csv_file=args.profile_dir/'regions_comparable.csv'
    with csv_file.open('w', encoding='utf-8-sig', newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['Region ID','Region name','Availability']+list(METRIC_COLUMNS))
        for profile in load_profiles(args.profile_dir):
            writer.writerow([profile.get('site_code'),profile.get('region_name'),profile.get('availability')]+
                            [metric_value(profile,key) for key in METRIC_COLUMNS])
    print(f"Profiles processed: {len(results)} | fully ready: {sum(r['status']=='ready' for r in results)}")
    print('Comparable CSV:',csv_file)
    print('Source statistics preserved; readable_metrics added to each JSON.')
if __name__ == '__main__':
    main()
