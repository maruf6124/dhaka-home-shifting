import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_tmp}/test.db"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOCAL_UPLOAD_DIR"] = f"{_tmp}/uploads"
os.environ["JOB_SECRET"] = "test-job-secret"

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services.email import OUTBOX  # noqa: E402

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
       b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")


@pytest_asyncio.fixture(autouse=True)
async def fresh_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    from scripts.seed import main as seed
    await seed()
    OUTBOX.clear()
    yield


def client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def last_code(email: str) -> str:
    return next(m["code"] for m in reversed(OUTBOX) if m["to"] == email and "code" in m)


async def signup(c: AsyncClient, name: str, email: str, phone: str, password: str = "password123") -> dict:
    r = await c.post("/auth/register", json={"name": name, "email": email, "phone": phone, "password": password})
    assert r.status_code == 201, r.text
    r = await c.post("/auth/verify-email", json={"email": email, "code": last_code(email)})
    assert r.status_code == 200, r.text
    return r.json()["user"]


async def make_admin(c: AsyncClient) -> None:
    from scripts.create_admin import main as create_admin
    await create_admin("Admin", "admin@example.com", "01700000000", "adminpass123")
    r = await c.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass123"})
    assert r.json()["status"] == "otp_required"
    r = await c.post("/auth/login/verify", json={"email": "admin@example.com", "code": last_code("admin@example.com")})
    assert r.status_code == 200, r.text


async def area_id(c: AsyncClient, name_en: str = "Mirpur-10") -> int:
    areas = (await c.get("/areas")).json()
    return next(a["id"] for a in areas if a["name_en"] == name_en)


@pytest.fixture
def anyio_backend():
    return "asyncio"


__all__ = ["client", "signup", "make_admin", "area_id", "last_code", "PNG", "SessionLocal"]
