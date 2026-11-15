"""Audit and actually analyse downloaded NASA GeoTIFF rasters for all regions.

Usage: python scripts/repair_all_region_data.py
       python scripts/repair_all_region_data.py --refresh-candidates
       python scripts/repair_all_region_data.py --audit-only
"""
import argparse
import csv
import json
import shutil
import sys
from datetime import datetime,timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_data.unified_regions import REGIONS
from selenekto_v2.raster_resolver import inventory
from selenekto_v2.actual_regions import regenerate,refresh_saved_candidates


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit-only',action='store_true',help='List real files; do not change JSON')
    parser.add_argument('--refresh-candidates',action='store_true',help='Update named candidate cell metrics, backing up existing store')
    args=parser.parse_args()
    raw=ROOT/'data/raw/lola'
    out=ROOT/'data/catalog/region_profiles'
    out.mkdir(parents=True,exist_ok=True)
    reports=[inventory(raw,code) for code in REGIONS]
    audit=out/'local_raster_inventory.json'
    audit.write_text(json.dumps({'timestamp_utc':datetime.now(timezone.utc).isoformat(),
                                 'root':str(raw),'regions':reports}, indent=2),encoding='utf-8')
    for rec in reports:
        print(f"{rec['region']:12} TIFF={rec['tiff_count']:<3} layers={rec['found_layers']}/5",flush=True)
        if rec['found_layers']<5:
            print('    FILES:',', '.join(rec['example_files']) or '(no files in region folder)',flush=True)
            print('    ISSUES:', '; '.join(rec['issues']),flush=True)
    print('Raster inventory:',audit,flush=True)
    if args.audit_only:return
    # Never overwrite the only known-good set of profiles without a dated backup.
    backup=ROOT/'data/processed'/('region_profiles_backup_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
    backup.mkdir(parents=True,exist_ok=True)
    for f in out.glob('*.json'):shutil.copy2(f,backup/f.name)
    for f in out.glob('*.csv'):shutil.copy2(f,backup/f.name)
    print('Previous JSON backup:',backup,flush=True)
    rows=regenerate(raw,out,REGIONS)
    print('COMPLETE:',sum(r['status']=='ready' for r in rows),'of',len(rows),'regions ready',flush=True)
    print('Compare CSV:',out/'regions_comparable.csv',flush=True)
    if args.refresh_candidates:
        result=refresh_saved_candidates(ROOT)
        print('CANDIDATES:',result,flush=True)
    if any(r['status']!='ready' for r in rows):
        print('Some folders lack usable raster layers. See local_raster_inventory.json for the actual filenames.',flush=True)

if __name__=='__main__':main()
