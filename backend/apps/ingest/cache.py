"""Download cache (SDD §12.3): raw downloads are kept on disk so re-runs don't refetch."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path
from typing import Any

from django.conf import settings


def cache_dir(*parts: str) -> Path:
    path = Path(settings.INGEST_CACHE_DIR, *parts)
    path.mkdir(parents=True, exist_ok=True)
    return path


def _request(url: str) -> urllib.request.Request:
    if not url.startswith("https://"):
        raise ValueError(f"Only https:// sources are allowed: {url}")
    return urllib.request.Request(url, headers={"User-Agent": settings.INGEST_USER_AGENT})


def download(url: str, dest: Path, *, retries: int = 4, timeout: int = 600) -> Path:
    """Fetch `url` to `dest` unless it is already there. Writes via a .part file."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(_request(url), timeout=timeout) as r, open(tmp, "wb") as f:
                expected = r.headers.get("Content-Length")
                shutil.copyfileobj(r, f, 1 << 20)
            size = tmp.stat().st_size
            if expected is not None and size != int(expected):  # connection dropped mid-file
                raise OSError(f"short download {size}/{expected} bytes: {url}")
            tmp.rename(dest)
            return dest
        except Exception:
            tmp.unlink(missing_ok=True)
            if attempt == retries - 1:
                raise
            time.sleep(5 * 2**attempt)
    raise AssertionError("unreachable")


def http_json(url: str, *, timeout: int = 60) -> Any:
    with urllib.request.urlopen(_request(url), timeout=timeout) as r:
        return json.load(r)


def http_text(url: str, *, timeout: int = 60) -> tuple[str, dict[str, str]]:
    """GET a small text resource; returns (body, headers)."""
    with urllib.request.urlopen(_request(url), timeout=timeout) as r:
        return r.read().decode(), dict(r.headers.items())


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(*parts: str) -> str:
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()
