from contextlib import asynccontextmanager

from fastapi import FastAPI

from engine.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.settings = settings
    yield


app = FastAPI(
    title="OASIS Simulation Engine",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/engine/health")
async def health():
    return {"status": "ok", "service": "oasis-engine"}
