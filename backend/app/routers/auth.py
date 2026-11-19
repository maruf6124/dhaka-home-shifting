"""Sign-up with email OTP, login (OTP only from a new device), refresh,
logout and password reset."""
from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, utcnow
from app.core.deps import ACCESS_COOKIE, DEVICE_COOKIE, REFRESH_COOKIE, get_current_user
from app.core.errors import AppError
from app.core.ratelimit import limiter
from app.core.security import (
    create_token, decode_token, hash_password, hash_secret, new_device_token, verify_password,
)
from app.models import TrustedDevice, User, UserRole
from app.schemas import EmailIn, LoginIn, OtpVerifyIn, RegisterIn, ResendIn, ResetIn
from app.services.email import send_email
from app.services.otp import check_otp, create_otp
from app.services.serializers import user_out
from app.services.settings_store import get_setting
from app.services.wallet import credit, lock_wallet

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


def _cookie(response: Response, name: str, value: str, max_age: int) -> None:
    response.set_cookie(
        name, value, max_age=max_age, httponly=True, secure=settings.cookie_secure,
        samesite=settings.cookie_samesite, domain=settings.cookie_domain, path="/",
    )


def _issue_tokens(response: Response, user_id: int) -> dict:
    access = create_token(user_id, "access")
    refresh = create_token(user_id, "refresh")
    _cookie(response, ACCESS_COOKIE, access, settings.access_token_minutes * 60)
    _cookie(response, REFRESH_COOKIE, refresh, settings.refresh_token_days * 86400)
    # Tokens are also returned so the WebSocket and non-browser clients can use them.
    return {"access_token": access, "refresh_token": refresh}


async def _trust_device(db: AsyncSession, response: Response, request: Request, user_id: int) -> None:
    token = new_device_token()
    db.add(TrustedDevice(
        user_id=user_id, token_hash=hash_secret(token),
        user_agent=(request.headers.get("user-agent") or "")[:255],
        expires_at=utcnow() + timedelta(days=settings.trusted_device_days),
    ))
    _cookie(response, DEVICE_COOKIE, token, settings.trusted_device_days * 86400)


async def _device_is_trusted(db: AsyncSession, request: Request, user_id: int) -> bool:
    token = request.cookies.get(DEVICE_COOKIE) or request.headers.get("x-device-token")
    if not token:
        return False
    device = (await db.execute(
        select(TrustedDevice).where(TrustedDevice.token_hash == hash_secret(token), TrustedDevice.user_id == user_id)
    )).scalar_one_or_none()
    if device is None or device.expires_at < utcnow():
        return False
    device.last_used_at = utcnow()
    return True


async def _user_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()


@router.post("/register", status_code=201)
@limiter.limit("10/hour")
async def register(request: Request, data: RegisterIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    existing = await _user_by_email(db, email)
    if existing is not None:
        if existing.email_verified_at is not None:
            raise AppError("email_taken", 409)
        # Unverified account: update details and send a fresh code.
        if existing.phone != data.phone:
            other = (await db.execute(select(User).where(User.phone == data.phone))).scalar_one_or_none()
            if other is not None:
                raise AppError("phone_taken", 409)
        existing.name, existing.phone = data.name, data.phone
        existing.password_hash = hash_password(data.password)
        existing.language = data.language
        user = existing
    else:
        if (await db.execute(select(User).where(User.phone == data.phone))).scalar_one_or_none():
            raise AppError("phone_taken", 409)
        user = User(name=data.name, email=email, phone=data.phone,
                    password_hash=hash_password(data.password), language=data.language)
        user.roles.append(UserRole(role="client", kyc_status="verified"))
        db.add(user)
    code = await create_otp(db, email, "signup")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError("email_taken", 409)
    background.add_task(send_email, email, "otp_signup", user.language, code=code)
    return {"status": "otp_sent", "email": email}


@router.post("/verify-email")
@limiter.limit("20/hour")
async def verify_email(request: Request, data: OtpVerifyIn, response: Response, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    if user is None:
        raise AppError("otp_invalid")
    await check_otp(db, email, "signup", data.code)
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    await lock_wallet(db, user.id)
    if not user.welcome_bonus_given:
        bonus = await get_setting(db, "welcome_bonus")
        if bonus:
            await credit(db, user.id, bonus=int(bonus), kind="bonus", note="welcome")
        user.welcome_bonus_given = True
    await _trust_device(db, response, request, user.id)
    await db.commit()
    tokens = _issue_tokens(response, user.id)
    return {"status": "ok", "user": await user_out(db, user), **tokens}


@router.post("/login")
@limiter.limit("10/minute")
async def login(request: Request, data: LoginIn, response: Response, background: BackgroundTasks,
                db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    if user is None or not verify_password(data.password, user.password_hash):
        raise AppError("bad_credentials", 401)
    if user.is_banned:
        raise AppError("banned", 403)
    if user.email_verified_at is None:
        code = await create_otp(db, email, "signup")
        await db.commit()
        background.add_task(send_email, email, "otp_signup", user.language, code=code)
        return {"status": "verify_email", "email": email}
    if await _device_is_trusted(db, request, user.id):
        await db.commit()
        tokens = _issue_tokens(response, user.id)
        return {"status": "ok", "user": await user_out(db, user), **tokens}
    code = await create_otp(db, email, "login")
    await db.commit()
    background.add_task(send_email, email, "otp_login", user.language, code=code)
    return {"status": "otp_required", "email": email}


@router.post("/login/verify")
@limiter.limit("20/hour")
async def login_verify(request: Request, data: OtpVerifyIn, response: Response, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    if user is None:
        raise AppError("otp_invalid")
    if user.is_banned:
        raise AppError("banned", 403)
    await check_otp(db, email, "login", data.code)
    await _trust_device(db, response, request, user.id)
    await db.commit()
    tokens = _issue_tokens(response, user.id)
    return {"status": "ok", "user": await user_out(db, user), **tokens}


@router.post("/resend-otp")
@limiter.limit("6/hour")
async def resend_otp(request: Request, data: ResendIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    # Same answer whether or not the account exists (no account probing).
    if user is not None and not (data.purpose == "signup" and user.email_verified_at is not None):
        code = await create_otp(db, email, data.purpose)
        await db.commit()
        background.add_task(send_email, email, f"otp_{data.purpose}", user.language, code=code)
    return {"status": "otp_sent"}


@router.post("/forgot-password")
@limiter.limit("6/hour")
async def forgot_password(request: Request, data: EmailIn, background: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    if user is not None:
        code = await create_otp(db, email, "reset")
        await db.commit()
        background.add_task(send_email, email, "otp_reset", user.language, code=code)
    return {"status": "otp_sent"}


@router.post("/reset-password")
@limiter.limit("20/hour")
async def reset_password(request: Request, data: ResetIn, db: AsyncSession = Depends(get_db)):
    email = data.email.lower()
    user = await _user_by_email(db, email)
    if user is None:
        raise AppError("otp_invalid")
    await check_otp(db, email, "reset", data.code)
    user.password_hash = hash_password(data.new_password)
    # A reset also proves the email address.
    if user.email_verified_at is None:
        user.email_verified_at = utcnow()
    # Log out every device.
    devices = (await db.execute(select(TrustedDevice).where(TrustedDevice.user_id == user.id))).scalars().all()
    for d in devices:
        await db.delete(d)
    await db.commit()
    return {"status": "ok"}


@router.post("/refresh")
async def refresh(request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        token = (body or {}).get("refresh_token")
    user_id = decode_token(token, "refresh") if token else None
    user = await db.get(User, user_id) if user_id else None
    if user is None or user.is_banned or not user.is_active:
        raise AppError("not_authenticated", 401)
    tokens = _issue_tokens(response, user.id)
    return {"status": "ok", **tokens}


@router.post("/logout")
async def logout(response: Response):
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        response.delete_cookie(name, path="/", domain=settings.cookie_domain,
                               secure=settings.cookie_secure, samesite=settings.cookie_samesite)
    return {"status": "ok"}


@router.get("/ws-token")
async def ws_token(user: User = Depends(get_current_user)):
    """Short-lived token for the chat WebSocket. The website talks to the API
    through its own /api proxy (first-party cookies), but WebSockets connect to
    the API directly, so they pass this token in the URL."""
    return {"token": create_token(user.id, "access")}


@router.get("/me")
async def me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    return await user_out(db, user)
