# Task ID: T011, T018 - FastAPI application entry point with health router
"""FastAPI application entry point.

Per Constitution Principle VI: MCP-Ready API Design
- REST endpoints with /api/v1/ prefix
- JSON request/response bodies
- CORS configured for frontend origin
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.api.health import router as health_router
from src.api.tasks import router as tasks_router
from src.db.session import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Create database tables if they don't exist
    await create_db_and_tables()
    yield
    # Shutdown: Cleanup if needed


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS middleware per Constitution Principle III
# Per clarification: CORS configured for frontend origins
# Note: Allow both localhost and 127.0.0.1 as browsers may use either
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.FRONTEND_URL,
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Task ID: T018 - Register health router
app.include_router(health_router, prefix=settings.API_V1_PREFIX)

# Task ID: T048 - Register tasks router
app.include_router(tasks_router, prefix=settings.API_V1_PREFIX)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
