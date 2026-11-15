"""Best-effort diagnostic logging for portable SelenEkto workers.

Never allow a log-file permissions error to mask the original science/API error.
No telemetry or network requests are made.
"""
from __future__ import annotations

import os
import tempfile
import traceback
from pathlib import Path


def write_worker_exception(root, filename: str, exc: BaseException) -> Path | None:
    if not filename or Path(filename).name != filename:
        raise ValueError("Log filename must be a simple filename")

    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    local_base = Path(
        os.environ.get("LOCALAPPDATA")
        or os.environ.get("XDG_STATE_HOME")
        or tempfile.gettempdir()
    )
    destinations = [
        Path(root) / "data" / "processed" / "logs" / filename,
        local_base / "SelenEkto" / "logs" / filename,
    ]
    for target in destinations:
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(details, encoding="utf-8")
            return target
        except OSError:
            # This location may be read-only or unavailable on a clean install.
            continue
    return None
