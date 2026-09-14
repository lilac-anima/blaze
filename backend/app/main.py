"""FastAPI application for Blaze."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import exceptions as neo4j_exc

from backend.app.database import get_driver, close_driver
from backend.app.models import HealthResponse

from backend.app.routers import (
    friends,
    users,
    events,
    camps,
    groups,
    posts,
    feed,
    sync,
)
from backend.app.auth.router import router as auth_router
from backend.app.auth.profile import router as profile_router

# ── CORS: allow the Vite dev server origin ────────────────────────────
ORIGINS = [
    "http://localhost:5173",      # Vite default
    "http://localhost:4173",      # Vite preview
    "http://127.0.0.1:5173",
    "http://127.0.0.1:4173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    await get_driver()  # Graceful — logs warning if Neo4j unavailable
    yield
    await close_driver()


app = FastAPI(
    title="Blaze API",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS Middleware ───────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register Routers ────────────────────────────────────────────────
app.include_router(friends.router)
app.include_router(users.router)
app.include_router(events.router)
app.include_router(camps.router)
app.include_router(groups.router)
app.include_router(posts.router)
app.include_router(feed.router)
app.include_router(sync.router)

# ── Auth & Profile ──────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(profile_router)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Verify the API and Neo4j connection are operational."""
    try:
        driver = await get_driver()
        if driver is None:
            return HealthResponse(status="degraded", neo4j_connected=False)

        async with driver.session() as session:
            try:
                result = await session.run("MATCH (n) RETURN count(n) AS node_count")
                node_count = await result.single()
                node_count = node_count["node_count"] if node_count else 0

                result = await session.run("MATCH ()-[r]->() RETURN count(r) AS rel_count")
                rel_count = await result.single()
                rel_count = rel_count["rel_count"] if rel_count else 0

                return HealthResponse(
                    status="ok",
                    neo4j_connected=True,
                    node_count=node_count,
                    relationship_count=rel_count,
                )
            except neo4j_exc.ServiceUnavailable:
                return HealthResponse(status="degraded", neo4j_connected=False)
    except Exception as e:
        return HealthResponse(
            status="error",
            neo4j_connected=False,
            detail=str(e),
        )
