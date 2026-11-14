from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.core.config import get_settings
from backend.app.api.routes import router as analysis_router
from backend.app.api.qa import qa_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Evidence-grounded legal contract intelligence and risk analysis API.",
    version="0.1.0",
    debug=settings.debug,
)

app.include_router(analysis_router)
app.include_router(qa_router)

# Keep CORS enabled for local development and optional separate frontends.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# In the Render Docker deployment, the Vite build is copied into this directory.
# Serving the UI and API from one origin avoids a manually configured API URL.
frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
frontend_index = frontend_dist / "index.html"
frontend_assets = frontend_dist / "assets"
if frontend_assets.is_dir():
    app.mount("/assets", StaticFiles(directory=frontend_assets), name="frontend-assets")


@app.get("/", tags=["system"])
def root():
    if frontend_index.is_file():
        return FileResponse(frontend_index)
    return {
        "name": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": settings.app_name,
        "environment": settings.app_env,
    }
