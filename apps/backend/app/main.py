from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.workers.scheduler import build_scheduler

logging.basicConfig(level=logging.INFO, format="%(message)s")

scheduler = build_scheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.scheduler_enabled and not scheduler.running:
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
