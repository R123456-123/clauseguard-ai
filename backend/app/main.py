"""ClauseGuard AI — FastAPI Application Entry Point.

Initializes the FastAPI application with CORS middleware configured
for the Next.js frontend, and mounts all API route handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router

app: FastAPI = FastAPI(
    title="ClauseGuard AI",
    description=(
        "AI-powered legal contract risk analysis tool. "
        "Extracts clauses, identifies risks, and generates negotiation prep packs "
        "using Google Gemini AI."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and production frontend
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 when the service is running."""
    return {"status": "healthy", "service": "clauseguard-ai"}
