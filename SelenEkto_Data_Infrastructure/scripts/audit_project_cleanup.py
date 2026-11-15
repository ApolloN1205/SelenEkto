"""Conservative project clean-up: report first, optionally move junk to archive.

Never deletes files; never traverses junctions/symlinks; preserves data, code, tests,
.git, build scripts and the working dist/SelenEkto release.
"""
import argparse
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

JUNK_DIRS={'__pycache__','.pytest_cache','.ruff_cache','.mypy_cache','.hypothesis'}
JUNK_FILES={'.DS_Store','Thumbs.db'}
PROTECTED_TOP={'.git','.venv','venv','data','src','tests','assets','release','dist','_archive'}


def candidates(root: Path):
    # Walk project tree but don't descend into TIFFs, venvs, source repositories,
    # symlinks/junctions, or the current distributable folder.
    skip={'data','.git','.venv','venv','dist','_archive','node_modules'}
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent=Path(base)
        keep=[]
        for d in dirs:
            child=parent/d
            if d in JUNK_DIRS and not child.is_symlink() and not os.path.isjunction(child):
                yield child, 'generated cache directory'
            elif d not in skip and not child.is_symlink() and not os.path.isjunction(child):
                keep.append(d)
        dirs[:]=keep
        for f in files:
            file=parent/f
            if f in JUNK_FILES and not file.is_symlink():
                yield file,'OS-generated cache file'


def run(root: Path, apply: bool=False):
    root=root.resolve()
    if not (root/'scripts').is_dir() or not (root/'src').is_dir():
        raise RuntimeError(f'This does not look like the infrastructure project root: {root}')
    found=list(candidates(root))
    total=0
    for p, reason in found:
        try:
            size=sum(f.stat().st_size for f in p.rglob('*') if f.is_file() and not f.is_symlink()) if p.is_dir() else p.stat().st_size
        except OSError:
            size=0
        total+=size
        print(('MOVE' if apply else 'KEEP / CANDIDATE'), str(p.relative_to(root)), reason, f'{size / 1048576:.2f} MiB')
    print(f'{len(found)} optional generated-cache entries, about {total / 1048576:.2f} MiB.')
    if not apply:
        print('DRY RUN: Nothing moved or deleted. Use --apply to quarantine only these cache entries.')
        return
    timestamp=datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    dest=root/'_archive'/('cleanup_'+timestamp)
    if found: dest.mkdir(parents=True,exist_ok=False)
    records=[]
    for p, reason in found:
        relative=p.relative_to(root)
        target=dest/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(p),str(target))
        records.append({'from':str(relative),'to':str(target.relative_to(root)),'reason':reason})
    if found:
        (dest/'cleanup_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
        print('Moved only generated caches to:',dest)
    print('No files were permanently deleted. Your NASA data, candidate files, code, and release remain untouched.')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply',action='store_true',help='Move safe generated caches into an archive (no deletion).')
    args=parser.parse_args()
    run(args.root,args.apply)
