import pytest

from tests.conftest import client, last_code, signup

pytestmark = pytest.mark.asyncio


async def test_signup_gives_welcome_bonus_once():
    async with client() as c:
        user = await signup(c, "Rahim", "rahim@example.com", "০১৭১১-২২২৩৩৩")
        assert user["phone"] == "01711222333"
        assert user["email_verified"] is True
        assert user["balance"] == 5 and user["bonus_balance"] == 5
        me = (await c.get("/auth/me")).json()
        assert me["balance"] == 5


async def test_duplicate_email_and_phone():
    async with client() as c:
        await signup(c, "Aa", "a@example.com", "01711000001")
        r = await c.post("/auth/register", json={"name": "Bb", "email": "a@example.com", "phone": "01711000002", "password": "password123"})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "email_taken"
        r = await c.post("/auth/register", json={"name": "Bb", "email": "b@example.com", "phone": "01711000001", "password": "password123"},
                         headers={"Accept-Language": "en"})
        assert r.status_code == 409
        assert r.json()["detail"]["message"] == "An account with this mobile number already exists"


async def test_login_needs_otp_only_on_new_device():
    async with client() as c:
        await signup(c, "Aa", "a@example.com", "01711000001")
        await c.post("/auth/logout")
        r = await c.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
        assert r.json()["status"] == "ok"  # same browser: device cookie is trusted
    async with client() as other_device:
        r = await other_device.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
        assert r.json()["status"] == "otp_required"
        r = await other_device.post("/auth/login/verify", json={"email": "a@example.com", "code": "000000"})
        assert r.status_code == 400
        r = await other_device.post("/auth/login/verify", json={"email": "a@example.com", "code": last_code("a@example.com")})
        assert r.json()["status"] == "ok"
        assert (await other_device.get("/auth/me")).status_code == 200


async def test_wrong_password_and_otp_lockout():
    async with client() as c:
        await signup(c, "Aa", "a@example.com", "01711000001")
    async with client() as c:
        r = await c.post("/auth/login", json={"email": "a@example.com", "password": "nope-nope"})
        assert r.status_code == 401
        await c.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
        for _ in range(4):
            r = await c.post("/auth/login/verify", json={"email": "a@example.com", "code": "000000"})
            assert r.status_code == 400
        r = await c.post("/auth/login/verify", json={"email": "a@example.com", "code": "000000"})
        assert r.json()["detail"]["code"] == "otp_locked"
        r = await c.post("/auth/login/verify", json={"email": "a@example.com", "code": last_code("a@example.com")})
        assert r.json()["detail"]["code"] == "otp_locked"


async def test_password_reset():
    async with client() as c:
        await signup(c, "Aa", "a@example.com", "01711000001")
        r = await c.post("/auth/forgot-password", json={"email": "a@example.com"})
        assert r.status_code == 200
        r = await c.post("/auth/reset-password", json={"email": "a@example.com", "code": last_code("a@example.com"), "new_password": "newpassword1"})
        assert r.status_code == 200
    async with client() as c:
        r = await c.post("/auth/login", json={"email": "a@example.com", "password": "newpassword1"})
        assert r.json()["status"] == "otp_required"  # devices were logged out


async def test_unverified_user_cannot_post():
    async with client() as c:
        await c.post("/auth/register", json={"name": "Aa", "email": "a@example.com", "phone": "01711000001", "password": "password123"})
        r = await c.post("/auth/login", json={"email": "a@example.com", "password": "password123"})
        assert r.json()["status"] == "verify_email"
        assert (await c.get("/wallet")).status_code == 401
