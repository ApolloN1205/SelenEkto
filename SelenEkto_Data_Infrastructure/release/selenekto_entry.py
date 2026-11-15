"""SelenEkto console-free Windows bootstrap with visible failure reporting.

This file runs inside PyInstaller, using the folder containing the exe as its root.
No separately installed Python interpreter is required.
"""
from __future__ import annotations

import ctypes
import os
import runpy
import sys
import tempfile
import traceback
from datetime import datetime
from pathlib import Path


def application_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def error_log_location(root: Path) -> Path:
    # Prefer a user-writable log for users who install in read-only folders.
    if os.name == 'nt':
        base = Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir())
        return base / 'SelenEkto' / 'logs' / 'startup_error.log'
    return root / 'data' / 'processed' / 'logs' / 'release_startup_error.log'


def log_failure(exc: BaseException) -> Path | None:
    trace = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    report = f'SelenEkto startup failure — {datetime.now().isoformat()}\nExecutable: {sys.executable}\nFrozen: {getattr(sys, "frozen", False)}\n\n{trace}\n'
    destinations = [error_log_location(application_root()), application_root() / 'data' / 'processed' / 'logs' / 'release_startup_error.log']
    for path in destinations:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(report, encoding='utf-8')
            return path
        except (OSError, PermissionError):
            pass
    return None


def notify_failure(exc: BaseException, path: Path | None) -> None:
    description = f'{type(exc).__name__}: {exc}'
    message = ('SelenEkto could not start.\n\n'
               + description[:700]
               + ('\n\nTechnical report:\n' + str(path) if path else '\n\nCould not write a technical report.')
               + '\n\nThe Windows app should not require a separate Python installation.')
    if os.name == 'nt':
        try:
            ctypes.windll.user32.MessageBoxW(None, message, 'SelenEkto — Startup error', 0x10)
            return
        except Exception:
            pass
    print(message, file=sys.stderr)


def main() -> None:
    root = application_root()
    script = root / 'scripts' / 'launch_selenekto_v2_controls.py'
    if not script.is_file():
        raise FileNotFoundError(f'Missing application launcher: {script}')
    os.chdir(root)
    src = str(root / 'src')
    if src not in sys.path:
        sys.path.insert(0, src)
    # runpy allows the existing desktop launcher to remain the single app entrypoint.
    runpy.run_path(str(script), run_name='__main__')


if __name__ == '__main__':
    try:
        main()
    except BaseException as exc:
        path = log_failure(exc)
        notify_failure(exc, path)
        sys.exit(1)
