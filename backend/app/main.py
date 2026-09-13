from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.middleware import security_middleware
from app.db.health import check_database


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.middleware("http")(security_middleware)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def api_root() -> dict[str, str]:
    return {
        "service": "arthadrishti-api",
        "message": "ArthaDrishti API foundation is running.",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "arthadrishti-api",
    }


@app.get("/health/db")
def database_health() -> dict[str, str]:
    check_database()
    return {
        "status": "ok",
        "database": "reachable",
    }
