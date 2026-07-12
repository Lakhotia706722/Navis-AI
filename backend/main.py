"""FastAPI backend entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routes import auth, projects, renders, assets
from backend.database import Base, engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown logic."""
    logger.info("Maritime AI Studio backend starting...")
    # Create tables if they don't exist (for local dev; migrations in prod)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="Yetrix Maritime AI Studio",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


# Wire in routers
app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(renders.router)
app.include_router(assets.router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
