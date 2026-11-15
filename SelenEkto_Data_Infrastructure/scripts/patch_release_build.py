"""Exclude old launcher backups from future dist builds, preserving builder backups."""
from pathlib import Path
from datetime import datetime, timezone
import py_compile

root=Path(__file__).resolve().parents[1]
p=root/'scripts'/'build_windows_release.py'
if not p.is_file():raise SystemExit('Missing build script: '+str(p))
s=p.read_text(encoding='utf-8')
old="shutil.copytree(root/'scripts', dest/'scripts', ignore=shutil.ignore_patterns('__pycache__','*.pyc'), dirs_exist_ok=True)"
new="shutil.copytree(root/'scripts', dest/'scripts', ignore=shutil.ignore_patterns('__pycache__','*.pyc','*_backup*.py','*_pre_*.py','*_before_*.py','*_pre_*.py','*.bak','*_old.py'), dirs_exist_ok=True)"
if new in s:print('Builder already patched.');raise SystemExit(0)
if s.count(old)!=1:raise SystemExit('Unexpected build script version; no changes made.')
b=p.with_name(p.stem+'_before_polish_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'.py')
b.write_bytes(p.read_bytes());p.write_text(s.replace(old,new),encoding='utf-8')
try:py_compile.compile(str(p),doraise=True)
except Exception as exc:p.write_bytes(b.read_bytes());raise SystemExit(f'Restored original builder: {exc}')
print('Builder now excludes known temporary/back-up script files. Backup:',b.name)
