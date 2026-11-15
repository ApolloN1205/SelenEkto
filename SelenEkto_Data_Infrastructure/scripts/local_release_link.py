"""Reattach a rebuilt local portable app to existing developer NASA TIFFs.

Never copies TIFFs. Creates a Windows directory junction only after strict checks.
Run from infrastructure repo root. This is NOT part of the public distribution.
"""
import argparse
import os
import subprocess
from pathlib import Path
import shutil


def connect(root: Path, dry_run: bool = False) -> None:
    if os.name != 'nt':
        raise RuntimeError('Windows only: this uses a Windows directory junction.')
    root = root.resolve()
    app = root/'dist'/'SelenEkto'
    exe = app/'SelenEkto.exe'
    source = root/'data'/'raw'/'lola'
    target = app/'data'/'raw'/'lola'
    if not exe.is_file():
        raise FileNotFoundError(f'Build first; missing {exe}')
    if not source.is_dir():
        raise FileNotFoundError(f'Missing NASA dataset folder {source}')
    if not any(source.rglob('*.tif')):
        raise RuntimeError(f'No TIFF files in {source}')
    if target.is_symlink() or (target.exists() and target.is_dir() and os.path.isjunction(target)):
        print('Existing junction: ', target)
    elif target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise RuntimeError(f'Refusing to replace a nonempty/unknown folder: {target}')
        if not dry_run:
            target.rmdir()
            subprocess.run(['cmd','/c','mklink','/J',str(target),str(source)], check=True)
        else:
            print('[DRY RUN] Replace empty target with junction:', target, '->', source)
    else:
        if dry_run:
            print('[DRY RUN] Create junction:', target, '->', source)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(['cmd','/c','mklink','/J',str(target),str(source)], check=True)
    # Preserve existing app profiles. Copy only metadata missing from the app.
    src_profiles = root/'data'/'catalog'/'region_profiles'
    dest_profiles = app/'data'/'catalog'/'region_profiles'
    copied = 0
    if src_profiles.is_dir():
        if not dry_run: dest_profiles.mkdir(parents=True, exist_ok=True)
        for src in src_profiles.iterdir():
            if src.is_file() and src.suffix.lower() in {'.json','.csv'}:
                dst = dest_profiles/src.name
                if not dst.exists():
                    if not dry_run: shutil.copy2(src,dst)
                    copied += 1
    candidates = root/'data'/'catalog'/'named_candidates.json'
    dest_candidates = app/'data'/'catalog'/'named_candidates.json'
    if candidates.is_file() and not dest_candidates.exists():
        if not dry_run:
            dest_candidates.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(candidates,dest_candidates)
        print('Copied existing candidate records (original untouched).' if not dry_run else '[DRY RUN] Copy candidate records.')
    print('Missing lightweight profiles copied:',copied)
    print('Original NASA TIFFs remain outside the portable application.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--dry-run',action='store_true')
    args=parser.parse_args()
    connect(args.root,args.dry_run)
