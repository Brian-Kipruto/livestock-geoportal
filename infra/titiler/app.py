"""TiTiler with a URL allow-list (SDD §13: prevents SSRF via ?url=).

Only datasets under TITILER_ALLOWED_PREFIXES (comma-separated, e.g. "s3://cogs/") are served.
"""

import os
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from titiler.core.errors import DEFAULT_STATUS_CODES, add_exception_handlers
from titiler.core.factory import TilerFactory

ALLOWED = tuple(p.strip() for p in os.environ.get("TITILER_ALLOWED_PREFIXES", "s3://cogs/").split(",") if p.strip())


def allowed_url(url: Annotated[str, Query(description="Dataset URL (allow-listed)")]) -> str:
    if not url.startswith(ALLOWED):
        raise HTTPException(status_code=403, detail="URL not in allow-list")
    return url


app = FastAPI(title="Geoportal raster tiles", docs_url="/docs")
cog = TilerFactory(path_dependency=allowed_url, router_prefix="/cog")
app.include_router(cog.router, prefix="/cog", tags=["COG"])
add_exception_handlers(app, DEFAULT_STATUS_CODES)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
