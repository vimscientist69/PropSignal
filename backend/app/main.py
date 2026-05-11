from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_health import router as health_router
from app.api.routes_jobs import router as jobs_router
from app.api.routes_ranking import router as ranking_router
from app.api.routes_runs_diagnostics import router as runs_diagnostics_router
from app.api.week3_errors import validation_error_response
from app.core.config import settings

app = FastAPI(title=settings.app_name)

app.add_exception_handler(RequestValidationError, validation_error_response)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(jobs_router, prefix=settings.api_prefix)
app.include_router(ranking_router, prefix=settings.api_prefix)
app.include_router(runs_diagnostics_router, prefix=settings.api_prefix)
