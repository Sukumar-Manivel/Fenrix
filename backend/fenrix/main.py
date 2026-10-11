from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from fenrix import __version__
from fenrix.api import public, router
from fenrix.config import get_settings
from fenrix.db import SessionLocal
from fenrix.seed import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db(SessionLocal)
    yield


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(title="Fenrix API", version=__version__, lifespan=lifespan,
                  description="Supply-chain triage for application portfolios: which app do we fix first?")
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",") if o.strip()],
                       allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.include_router(public)
    app.include_router(router)

    static = Path(s.static_dir) if s.static_dir else None
    if static and (static / "index.html").exists():
        app.mount("/_next", StaticFiles(directory=static / "_next"), name="next-assets")

        @app.get("/{path:path}", include_in_schema=False)
        def dashboard(path: str):
            target = (static / path).resolve()
            if static.resolve() not in target.parents and target != static.resolve():
                return FileResponse(static / "404.html", status_code=404)
            if target.is_dir():
                target = target / "index.html"
            if target.is_file():
                return FileResponse(target)
            return FileResponse(static / "404.html", status_code=404)

    return app


app = create_app()
