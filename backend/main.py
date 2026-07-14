"""FastAPI backend entrypoint — Phase 11."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import auth, projects, renders, assets
from backend.routes import workspaces
from backend.database import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Maritime AI Studio backend starting (Phase 11 — Workspaces)...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Yetrix Maritime AI Studio",
    version="0.11.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.11.0"}


# Routers
app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(projects.router)
app.include_router(renders.router)
app.include_router(assets.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
