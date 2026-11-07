from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import admin_ops, auth, calc, runs, simulation_stream

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Lunar Landing Site Navigator API",
    version="0.2.0",
    description="Team API with auth and run history; validated lunar geometry gated separately.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings["allowed_origins"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type", "X-CSRF-Token"],
)

app.include_router(auth.router)
app.include_router(runs.router)
app.include_router(calc.router)
app.include_router(simulation_stream.router)
app.include_router(admin_ops.router)


@app.get("/health")
def health():
    ready = settings["science_calculations_ready"]
    return {
        "status": "ok",
        "service": "lunar-landing-site-navigator-api",
        "api_version": app.version,
        "science_calculations_ready": ready,
        "message": (
            "Service is reachable; validated lunar calculations are enabled."
            if ready
            else "Service is reachable; validated lunar calculations are not implemented."
        ),
        "auth": {
            "github_oauth_configured": bool(settings["api_github_client_id"]),
            "separate_from_jupyterhub": True,
        },
    }
