"""Run from project root: python scripts/build_all_region_json.py"""
from __future__ import annotations
import argparse, csv, json, sys, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from selenekto_data.region_profiles import generate_catalogue
try:
    from selenekto_data.unified_regions import REGIONS
except ImportError:
    print('ERROR: missing src/selenekto_data/unified_regions.py; install the multi-region add-on first.', file=sys.stderr)
    raise SystemExit(2)

def main():
    parser=argparse.ArgumentParser(description='Generate Git-friendly JSON terrain profiles for all supported NASA regions')
    parser.add_argument('--regions',nargs='*',choices=list(REGIONS))
    args=parser.parse_args()
    regions={k: REGIONS[k] for k in (args.regions or REGIONS)}
    root=ROOT/'data/raw/lola'
    output=ROOT/'data/catalog/region_profiles'
    print('Raw GeoTIFF source:',root,flush=True)
    print('Versionable JSON output:',output,flush=True)
    print('Profiling',len(regions),'regions. Missing datasets will be explicitly marked.',flush=True)
    rows=[]
    for row in generate_catalogue(root,output,regions):
        rows.append(row)
        print(f"[{len(rows)}/{len(regions)}] {row['site_code']}: {row['status']} ({row['valid_layers']}/5 layers)",flush=True)
        for err in row['errors']:
            print('    ',err,flush=True)
    csvpath=output/'regions_index.csv'
    with csvpath.open('w',newline='',encoding='utf-8') as handle:
        writer=csv.DictWriter(handle,fieldnames=['site_code','region_name','status','valid_layers','file','errors'])
        writer.writeheader()
        for r in rows: writer.writerow({**r,'errors':' | '.join(r['errors'])})
    print('\nCompleted. Profiles:',len(rows),'ready:',sum(r['status']=='ready' for r in rows))
    print('Browse:',output)
    print('IMPORTANT: JSON contains summaries, not full-resolution raster pixels or solar timelines.')

if __name__=='__main__':
    try: main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
