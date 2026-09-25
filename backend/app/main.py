"""ClauseGuard AI — FastAPI Application Entry Point.

Initializes the FastAPI application with CORS middleware configured
for the Next.js frontend, and mounts all API route handlers.
"""

import os
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
_cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

_rate_limit_requests = int(os.getenv("RATE_LIMIT_REQUESTS", "30"))
_rate_limit_window = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
_request_timestamps: defaultdict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def rate_limit_ai_requests(request: Request, call_next):
    """Limit expensive API calls per client in this application instance."""
    if request.method == "POST" and request.url.path.startswith("/api/v1/"):
        client_host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        timestamps = _request_timestamps[client_host]
        while timestamps and timestamps[0] <= now - _rate_limit_window:
            timestamps.popleft()
        if len(timestamps) >= _rate_limit_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again shortly.",
                    "error_code": "RATE_LIMITED",
                },
                headers={"Retry-After": str(_rate_limit_window)},
            )
        timestamps.append(now)

    return await call_next(request)

# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------
app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Liveness probe — returns 200 when the service is running."""
    return {"status": "healthy", "service": "clauseguard-ai"}
