"""Rebuild all 27 region profiles from local raster pixels, refresh candidate measurements."""
from pathlib import Path
import argparse
import sys
import shutil
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_v2.actual_regions import regenerate,refresh_saved_candidates,source_regions

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--region',action='append',help='Run one region; repeat for multiple regions')
    p.add_argument('--skip-candidates',action='store_true')
    args=p.parse_args()
    try:
        from selenekto_data.unified_regions import REGIONS
        known=dict(REGIONS)
    except ImportError:
        known={}
    raw=ROOT/'data/raw/lola'
    for code in source_regions(raw):known.setdefault(code,code)
    if args.region:
        selection={code:known.get(code,code) for code in args.region}
    else:selection=known
    if not selection:raise SystemExit('No catalogued regions or rasters detected. Check local data/raw/lola directory.')
    print('SelenEkto / ACTUAL NASA TERRAIN DATA',flush=True)
    print('Raw folder:',raw,flush=True)
    existing=ROOT/'data/catalog/region_profiles'
    backup=ROOT/'data/processed/region_profiles_backup_before_v2_rebuild'
    if existing.is_dir() and not backup.exists():
        backup.mkdir(parents=True,exist_ok=True)
        for path in existing.glob('*.json'):
            shutil.copy2(path,backup/path.name)
        for path in existing.glob('*.csv'):
            shutil.copy2(path,backup/path.name)
        print('Existing profile backup:',backup,flush=True)
    rows=regenerate(raw, existing,selection)
    print(f"COMPLETED: {len(rows)} profiles; {sum(r['status']=='ready' for r in rows)} complete/ready; {sum(r['status']!='ready' for r in rows)} incomplete/invalid",flush=True)
    if not args.skip_candidates:
        result=refresh_saved_candidates(ROOT)
        print(f"CANDIDATES: {result['updated']}/{result['count']} refreshed; {result['unavailable']} unavailable",flush=True)
        for error in result['errors']:print('  '+error,flush=True)
    print('JSON files: data/catalog/region_profiles/',flush=True)
    print('Comparison CSV: data/catalog/region_profiles/regions_comparable.csv',flush=True)
if __name__=='__main__':main()
