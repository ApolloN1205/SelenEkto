"""Measure portable release size without following NASA directory junctions."""
import argparse
import os
from pathlib import Path


def report(root: Path):
    release=root/'dist'/'SelenEkto'
    if not (release/'SelenEkto.exe').is_file():
        raise FileNotFoundError(f'Missing built application: {release / "SelenEkto.exe"}')
    sizes=[]; junctions=[]
    for base, dirs, files in os.walk(release,followlinks=False):
        directory=Path(base)
        safe=[]
        for name in dirs:
            child=directory/name
            if child.is_symlink() or os.path.isjunction(child):
                junctions.append(child.relative_to(release))
            else: safe.append(name)
        dirs[:]=safe
        for name in files:
            item=directory/name
            if item.is_symlink():continue
            try: size=item.stat().st_size
            except OSError:continue
            sizes.append((item.relative_to(release),size))
    total=sum(size for _,size in sizes)
    print(f'Portable build: {len(sizes)} files, {total/(1024**2):,.1f} MiB (excludes junction targets)')
    print('Ten largest files:')
    for name,size in sorted(sizes,key=lambda row:row[1],reverse=True)[:10]:
        print(f'  {size/(1024**2):8.1f} MiB  {name}')
    tiffs=[(name,size) for name,size in sizes if name.suffix.lower() in ('.tif','.tiff')]
    print(f'Bundled NASA TIFFs: {len(tiffs)}; {sum(s for _,s in tiffs)/(1024**2):.1f} MiB')
    for j in junctions:print('External link (not part of upload):',j)
    print('Note: distribute a ZIP of the actual folder, NOT a local junction-linked dataset.')
    if tiffs:
        print('WARNING: TIFF files bundled; review before publishing.')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
    report(args.root.resolve())
