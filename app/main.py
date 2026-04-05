import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import dashboard, records, users
from app.database import create_db_and_tables, seed_role_permissions
from app.exceptions import AppError
from app.rate_limit import limiter


@asynccontextmanager
async def lifespan(_: FastAPI):
    if os.getenv("FINANCE_SKIP_DB_INIT") == "1":
        yield
        return
    create_db_and_tables()
    seed_role_permissions()
    yield


app = FastAPI(
    title="Finance Backend",
    description="REST API with JWT auth, policy-based RBAC, and SQL-backed analytics.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error,
            "message": exc.message,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    detail = exc.detail
    if isinstance(detail, dict) and "error" in detail and "message" in detail:
        body = {
            "error": detail["error"],
            "message": detail["message"],
            "status_code": exc.status_code,
        }
    else:
        body = {
            "error": "http_error",
            "message": str(detail),
            "status_code": exc.status_code,
        }
    return JSONResponse(status_code=exc.status_code, content=body)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError):
    errs = exc.errors()
    first = errs[0] if errs else {}
    loc = ".".join(str(x) for x in first.get("loc", []) if x != "body")
    msg = first.get("msg", "Invalid request body.")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "validation_error",
            "message": f"{loc}: {msg}" if loc else msg,
            "status_code": 400,
        },
    )


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(users.router)
app.include_router(records.router)
app.include_router(dashboard.router)
