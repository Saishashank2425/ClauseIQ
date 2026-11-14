from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

# Public, cookie-free API for the separately hosted demo frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
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
