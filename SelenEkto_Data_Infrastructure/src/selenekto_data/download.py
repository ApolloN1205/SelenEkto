"""Cautious, resumable downloader for officially listed SelenEkto data products."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .paths import project_root

DEFAULT_MAX_BYTES = 500 * 1024 * 1024
ALLOWED_HOSTS = {"pgda.gsfc.nasa.gov", "ntrs.nasa.gov", "ssd.jpl.nasa.gov", "ssd-api.jpl.nasa.gov",
                 "pds-geosciences.wustl.edu", "pds.nasa.gov", "naif.jpl.nasa.gov"}


class DownloadError(RuntimeError):
    """Raised when a download cannot safely complete."""


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_destination(root: Path, relative_path: str) -> Path:
    rel = Path(relative_path)
    if rel.is_absolute() or ".." in rel.parts:
        raise DownloadError(f"Unsafe local path in registry: {relative_path}")
    destination = (root / rel).resolve()
    if root.resolve() not in destination.parents and destination != root.resolve():
        raise DownloadError(f"Destination escapes repository: {relative_path}")
    return destination


def _record_json(path: Path, record: dict[str, Any]) -> None:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
    else:
        payload = {"schema_version": "1.0", "records": []}
    payload.setdefault("records", []).append(record)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _update_dataset_manifest(root: Path, dataset_id: str, **updates: Any) -> None:
    path = root / "data/manifests/datasets.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for item in payload["datasets"]:
        if item["dataset_id"] == dataset_id:
            item.update(updates)
            break
    else:
        raise DownloadError(f"Dataset {dataset_id} not present in registry")
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def download_dataset(dataset: dict[str, Any], root: Path | None = None, *,
                     max_bytes: int = DEFAULT_MAX_BYTES, timeout: int = 45,
                     user_agent: str = "SelenEkto-DataLayer/0.1") -> dict[str, Any]:
    """Download one registry product, resuming partial data when the server supports Range.

    The default hard cap is 500 MiB. Oversized products are refused unless the caller
    explicitly supplies a larger cap. Only HTTPS URLs on the allowlist are accepted.
    """
    base = (root or project_root()).resolve()
    parsed = urllib.parse.urlparse(dataset["download_url"])
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS:
        raise DownloadError(f"Refusing non-HTTPS or non-allowlisted URL: {dataset['download_url']}")

    destination = _safe_destination(base, dataset["local_path"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")

    if destination.exists():
        existing_hash = sha256_file(destination)
        result = {"status": "already_present", "path": str(destination.relative_to(base)),
                  "size_bytes": destination.stat().st_size, "sha256": existing_hash}
        _update_dataset_manifest(base, dataset["dataset_id"], acquisition_status="downloaded",
                                 validation_status="checksum_calculated", retrieval_date=_now(),
                                 file_size_bytes=result["size_bytes"], sha256=existing_hash)
        return result

    existing_size = partial.stat().st_size if partial.exists() else 0
    if existing_size > max_bytes:
        raise DownloadError(f"Partial file already exceeds the {max_bytes}-byte size limit")

    headers = {"User-Agent": user_agent, "Accept": "*/*"}
    if existing_size:
        headers["Range"] = f"bytes={existing_size}-"
    request = urllib.request.Request(dataset["download_url"], headers=headers)
    started = time.monotonic()
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _update_dataset_manifest(base, dataset["dataset_id"], acquisition_status="download_failed_or_incomplete")
        raise DownloadError(f"Download request failed; partial file retained if present: {exc}") from exc

    with response:
        final_url = urllib.parse.urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname not in ALLOWED_HOSTS:
            raise DownloadError(f"Download redirected to a non-allowlisted host: {response.geturl()}")
        status = getattr(response, "status", response.getcode())
        if existing_size and status == 206:
            content_range = response.headers.get("Content-Range", "")
            match = re.match(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", content_range, re.IGNORECASE)
            if not match or int(match.group(1)) != existing_size:
                raise DownloadError(
                    f"Server returned an invalid Content-Range for resume at byte {existing_size}: {content_range!r}"
                )
            mode = "ab"
            append_size = existing_size
        else:
            # A server that ignores Range returns 200; restart rather than append duplicate bytes.
            mode = "wb"
            append_size = 0
            existing_size = 0

        content_length = response.headers.get("Content-Length")
        if content_length and append_size + int(content_length) > max_bytes:
            raise DownloadError(
                f"Server reports {append_size + int(content_length):,} bytes, exceeding the "
                f"{max_bytes:,}-byte limit. Choose a smaller product or explicitly raise the cap."
            )

        downloaded = append_size
        try:
            with partial.open(mode) as handle:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    downloaded += len(chunk)
                    if downloaded > max_bytes:
                        raise DownloadError(f"Download exceeded size limit ({max_bytes:,} bytes)")
                    handle.write(chunk)
                handle.flush()
                os.fsync(handle.fileno())
        except Exception:
            # Keep .part for a later Range resume; never promote incomplete data.
            raise

    if not partial.exists() or partial.stat().st_size == 0:
        raise DownloadError("Server returned an empty file")
    digest = sha256_file(partial)
    os.replace(partial, destination)
    size = destination.stat().st_size
    record = {
        "dataset_id": dataset["dataset_id"], "status": "downloaded",
        "retrieval_date_utc": _now(), "url": dataset["download_url"],
        "local_path": str(destination.relative_to(base)), "size_bytes": size,
        "sha256": digest, "elapsed_seconds": round(time.monotonic() - started, 2),
        "http_status": status,
    }
    _record_json(base / "data/manifests/acquisition_log.json", record)
    _update_dataset_manifest(base, dataset["dataset_id"], acquisition_status="downloaded",
                             validation_status="checksum_calculated", retrieval_date=_now(),
                             file_size_bytes=size, sha256=digest)
    return record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
