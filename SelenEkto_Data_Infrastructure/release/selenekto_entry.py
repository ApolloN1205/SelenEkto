"""Console-free PyInstaller bootstrap. Application data is beside the executable."""
from __future__ import annotations
import os
import runpy
import sys
from pathlib import Path


def application_root() -> Path:
    return Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]


def main() -> None:
    root = application_root()
    script = root / 'scripts' / 'launch_selenekto_v2_controls.py'
    if not script.is_file():
        raise RuntimeError('SelenEkto launcher is missing: ' + str(script))
    (root / 'data' / 'processed' / 'logs').mkdir(parents=True, exist_ok=True)
    os.chdir(root)
    sys.path.insert(0, str(root / 'src'))
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except BaseException:
        import traceback
        try:
            path = application_root() / 'data' / 'processed' / 'logs' / 'release_startup_error.log'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(traceback.format_exc(), encoding='utf-8')
        except Exception:
            pass
        raise
