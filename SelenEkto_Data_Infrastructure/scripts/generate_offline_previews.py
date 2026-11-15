"""Generate compact reference-only slope preview PNGs from installed NASA TIFFs."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from selenekto_v2.offline_library import REGIONS,generate_preview

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--region',choices=REGIONS)
    args=p.parse_args();good=0
    for region in ([args.region] if args.region else REGIONS):
        try:
            path=generate_preview(ROOT,region)
            print(f'OK {region}: {path} ({path.stat().st_size/1024:.0f} KiB)')
            good+=1
        except (FileNotFoundError,ValueError) as exc:
            print(f'SKIP {region}: {exc}')
    print(f'{good}/{1 if args.region else len(REGIONS)} lightweight previews created')
    if not good:raise SystemExit('No previews created; check original slope TIFFs')
if __name__=='__main__':main()
