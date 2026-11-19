from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler, message, pick_lang
from app.core.ratelimit import limiter
from app.routers import account, admin, auth, chat, internal, rent, trust, wallet

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0",
              docs_url="/docs" if settings.environment != "production" else None)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limited(request: Request, exc: RateLimitExceeded):
    lang = pick_lang(request)
    return JSONResponse(status_code=429, content={"detail": {"code": "rate_limited", "message": message("rate_limited", lang)}})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    lang = pick_lang(request)
    fields = [".".join(str(p) for p in e["loc"] if p != "body") for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": {"code": "invalid", "message": message("invalid", lang), "fields": fields}})


for module in (auth, account, rent, trust, wallet, chat, admin, internal):
    app.include_router(module.router)

# Public listing photos in local-storage mode (development only).
public_dir = Path(settings.local_upload_dir) / "public"
public_dir.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=public_dir), name="media")


@app.get("/health")
async def health():
    return {"status": "ok"}
