from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

# Per-IP limits. Behind Render's proxy the client IP comes from X-Forwarded-For,
# which uvicorn passes through with --proxy-headers.
limiter = Limiter(key_func=get_remote_address, enabled=get_settings().environment != "test")
