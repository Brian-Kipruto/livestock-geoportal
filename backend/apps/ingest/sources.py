"""Remote catalogues used by the pipelines (SDD Appendix A).

- Digital Earth Africa STAC: public COGs on AWS af-south-1, read anonymously.
- Microsoft Planetary Computer STAC: public, but blob URLs need a short-lived SAS token per
  storage container (fetched anonymously from the PC token endpoint).
"""

from __future__ import annotations

import threading
import time
from datetime import date
from urllib.parse import urlparse

import pystac
import pystac_client
from django.conf import settings

from .cache import http_json

DEA_STAC_DEFAULT = "https://explorer.digitalearth.africa/stac"
PC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"
PC_SAS_ENDPOINT = "https://planetarycomputer.microsoft.com/api/sas/v1/token/{account}/{container}"

DEA_ENV = {"AWS_NO_SIGN_REQUEST": "YES", "AWS_REGION": "af-south-1"}


def dea_client() -> pystac_client.Client:
    url = getattr(settings, "DEA_STAC_URL", "") or DEA_STAC_DEFAULT
    return pystac_client.Client.open(url, headers={"User-Agent": settings.INGEST_USER_AGENT})


def pc_client() -> pystac_client.Client:
    return pystac_client.Client.open(PC_STAC, headers={"User-Agent": settings.INGEST_USER_AGENT})


def search(
    client: pystac_client.Client,
    collection: str,
    bbox: tuple[float, float, float, float],
    start: date,
    end: date,
    **kw,
) -> list[pystac.Item]:
    """Items intersecting bbox in [start, end], searched one calendar year at a time.

    Long ranges in one search page slowly (Planetary Computer stalled on 26 years of MODIS);
    yearly chunks keep every request small. Items are de-duplicated by id.
    """
    items: dict[str, pystac.Item] = {}
    for year in range(start.year, end.year + 1):
        lo = max(start, date(year, 1, 1))
        hi = min(end, date(year, 12, 31))
        res = client.search(
            collections=[collection],
            bbox=list(bbox),
            datetime=f"{lo.isoformat()}/{hi.isoformat()}T23:59:59Z",
            limit=250,
            method="GET",
            **kw,
        )
        for it in res.items():
            items[it.id] = it
    return list(items.values())


def gdal_path(href: str) -> str:
    """s3:// → /vsis3/ (anonymous, via DEA_ENV); http(s) → /vsicurl/."""
    if href.startswith("s3://"):
        return "/vsis3/" + href[5:]
    if href.startswith("http"):
        return "/vsicurl/" + href
    return href


class PcSigner:
    """Caches one SAS token per Azure storage container; refreshes 5 min before expiry."""

    def __init__(self):
        self._tokens: dict[tuple[str, str], tuple[str, float]] = {}
        self._lock = threading.Lock()

    def sign(self, href: str) -> str:
        u = urlparse(href)
        account = u.netloc.split(".")[0]
        container = u.path.lstrip("/").split("/")[0]
        with self._lock:
            tok, expiry = self._tokens.get((account, container), ("", 0.0))
            if time.time() > expiry - 300:
                data = http_json(PC_SAS_ENDPOINT.format(account=account, container=container))
                tok = data["token"]
                expiry = time.time() + 45 * 60  # tokens live ≥ 1 h; refresh well before
                self._tokens[(account, container)] = (tok, expiry)
        return f"{href}?{tok}"
