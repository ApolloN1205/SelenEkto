#!/usr/bin/env python3
"""Fix path leakage in *staged* SelenEkto JSON, then install a persistent release-gate hook.

Never modifies source scientific profiles or TIFFs. Backs up original staged JSON
outside the published application. Unknown private paths cause refusal, not guessing.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

# Anchors that are safe to keep as portable relative references. All output uses '/'.
ANCHORS = ('data/raw/lola/', 'data/catalog/', 'data/processed/', 'assets/')
PRIVATE = re.compile(r'(?i)(?:[a-z]:[\\/]+users[\\/]+[^\\/\s"\']+|/users/[^/\s]+|/home/[^/\s]+)')
WINDOWS_ABSOLUTE = re.compile(r'(?i)^[a-z]:[\\/]')


def safe_string(value: str) -> str:
    """Preserve scientific metadata and replace machine paths by anchored relative paths."""
    if not PRIVATE.search(value):
        return value
    normalized = value.replace('\\', '/')
    lower = normalized.lower()
    matches = [(lower.find(a), a) for a in ANCHORS if lower.find(a) >= 0]
    if not matches:
        raise ValueError('Private path has no portable asset anchor (refusing to invent a replacement)')
    index, _ = min(matches)
    # Only transform a pure file/directory path or 'file://' path. Freeform descriptions
    # could contain additional private information and must be inspected instead.
    prefix = normalized[:index]
    if not (WINDOWS_ABSOLUTE.match(prefix) or prefix.lower().startswith('file:///') or prefix.startswith('/')):
        raise ValueError('Ambiguous private path inside text; manual inspection required')
    return normalized[index:]


def clean_obj(value):
    if isinstance(value, dict):
        return {k: clean_obj(v) for k,v in value.items()}
    if isinstance(value, list):
        return [clean_obj(v) for v in value]
    if isinstance(value, str):
        return safe_string(value)
    return value


def sanitize_stage(stage: Path, backup_dir: Path) -> tuple[int,int]:
    profiles = stage/'data'/'catalog'/'region_profiles'
    if not profiles.is_dir():
        raise FileNotFoundError(f'Profiles missing from stage: {profiles}')
    planned = []
    for file in sorted(profiles.glob('*.json')):
        if file.name == 'local_raster_inventory.json':
            planned.append((file, None))
            continue
        data = json.loads(file.read_text(encoding='utf-8'))
        new = clean_obj(data)
        result = json.dumps(new, ensure_ascii=False, indent=2) + '\n'
        if PRIVATE.search(result):
            raise ValueError(f'Private path still present: {file.name}')
        if file.read_text(encoding='utf-8') != result:
            planned.append((file, result))
    # Refuse modifications if another text file still contains a private path; final
    # release gate will make its own independent, full stage audit after this step.
    if not planned:
        return 0,0
    backup_dir.mkdir(parents=True, exist_ok=False)
    rewritten=removed=0
    for file, result in planned:
        shutil.copy2(file, backup_dir/file.name)
        if result is None:
            file.unlink(); removed+=1
        else:
            file.write_text(result, encoding='utf-8'); rewritten+=1
    return rewritten,removed


def install_gate_hook(gate: Path) -> bool:
    original = gate.read_text(encoding='utf-8')
    hook = '''    # Sanitize staged profiles, not the development originals.\n    from fix_release_profile_privacy import sanitize_stage\n    privacy_backup = root/'release_ready'/('privacy_backups_'+stamp())\n    changed, removed = sanitize_stage(stage, privacy_backup)\n    print(f'Staged privacy sanitization: {changed} profiles converted; {removed} inventory files excluded')\n'''
    needle = '    copy_portable(current,stage)\n'
    if 'from fix_release_profile_privacy import sanitize_stage' in original:
        return False
    if original.count(needle) != 1:
        raise RuntimeError('Unexpected final_release_gate.py layout; no changes made')
    patched = original.replace(needle,needle+hook,1)
    compile(patched, str(gate), 'exec')
    backup = gate.with_name(gate.stem+'_before_privacy_fix_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'.py.bak')
    shutil.copy2(gate, backup)
    gate.write_text(patched,encoding='utf-8')
    print('Future release-gate builds will sanitize staged JSON automatically.')
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path)
    args=ap.parse_args()
    root=(args.root or Path(__file__).resolve().parents[1]).resolve()
    gate=root/'scripts'/'final_release_gate.py'
    if not gate.is_file():
        raise FileNotFoundError(f'Cannot find release gate: {gate}')
    stages=sorted((root/'release_ready').glob('staging_*/SelenEkto'),key=lambda p:p.parent.name)
    if not stages:
        raise FileNotFoundError('No staged release found. Run final_release_gate.py prepare first.')
    stage=stages[-1]
    print('Repairing latest staged release:',stage)
    backup_dir=root/'release_ready'/('privacy_backups_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S'))
    rewritten,removed=sanitize_stage(stage,backup_dir)
    print(f'Staged profiles converted: {rewritten}; inventory removed: {removed}')
    print('Original staged versions saved outside distributable:', backup_dir if backup_dir.exists() else '(no changes needed)')
    # Independent audit using the existing, unmodified release gate's own rules.
    spec=importlib.util.spec_from_file_location('final_release_gate',gate)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report=module.audit(stage)
    module.write_result(stage, report)
    # Pointer is only created after the entire release gate audit passes.
    pointer=root/'release_ready'/'latest_stage.txt'
    pointer.write_text(str(stage)+'\n',encoding='utf-8')
    install_gate_hook(gate)
    print('AUDIT PASSED; release stage ready for independent Windows smoke test:',stage)
    print('Do NOT claim downloader verification until tested in the clean staged application.')

if __name__=='__main__':
    main()
