import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Lunar Landing Site Navigator API",
    version="0.1.0",
    description="Early service scaffold; no lunar geometry is calculated yet.",
)

origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS",
        "https://m9nx.github.io,http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=[],
)


@app.get("/health")
def health():
    """Report service availability separately from scientific readiness."""
    return {
        "status": "ok",
        "service": "lunar-landing-site-navigator-api",
        "api_version": app.version,
        "science_calculations_ready": False,
        "message": "Service is reachable; validated lunar calculations are not implemented.",
    }
