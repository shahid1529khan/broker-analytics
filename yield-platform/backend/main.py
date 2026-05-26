import os
import logging
import httpx
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from postgrest.exceptions import APIError
from backend.api.routes import clients, uploads, analytics, export, aggregators
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app = FastAPI(
    title="Yield Platform API",
    description="Backend API for the Yield Business Brokers commission analysis platform.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clients.router, prefix="/api/clients", tags=["Clients"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["Uploads"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(export.router, prefix="/api/export", tags=["Export"])
app.include_router(aggregators.router, prefix="/api/aggregators", tags=["Aggregators"])


@app.exception_handler(httpx.HTTPError)
async def httpx_exception_handler(request: Request, exc: httpx.HTTPError):
    logger.warning("External service connection failed on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content={"detail": "External service temporarily unavailable. Please retry."},
    )


@app.exception_handler(APIError)
async def postgrest_exception_handler(request: Request, exc: APIError):
    logger.warning("Database request failed on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=502,
        content={"detail": "Database request failed.", "error": str(exc)},
    )


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "version": "1.0.0"}
