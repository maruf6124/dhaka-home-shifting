"""End-to-end business flow: KYC → post → unlock → chat → report → refund → top-up."""
import pytest

from tests.conftest import PNG, area_id, client, make_admin, signup

pytestmark = pytest.mark.asyncio


def flat(area: int, **kw) -> dict:
    data = {
        "type": "entire_flat", "area_id": area, "title": "৩ বেড ফ্ল্যাট মিরপুর ১০",
        "description": "দক্ষিণমুখী। কল করুন ০১৭১২-৩৪৫৬৭৮ অথবা mail me at x@y.com",
        "rent": 18000, "service_charge": 2000, "advance_months": 2, "rooms": 3, "baths": 2,
        "tenant_type": "family", "amenities": ["lift", "gas"], "road_no": "6", "house_no": "14/B",
        "contact_phone": "01712345678",
    }
    data.update(kw)
    return data


async def become_landlord(c, admin_c) -> None:
    for doc in ("nid_front", "nid_back", "utility_bill"):
        r = await c.post("/kyc/documents", data={"role": "landlord", "doc_type": doc}, files={"file": ("a.png", PNG, "image/png")})
        assert r.status_code == 201, r.text
    assert (await c.post("/kyc/landlord/submit")).json()["status"] == "pending"
    queue = (await admin_c.get("/admin/kyc")).json()
    assert queue[0]["role"] == "landlord" and len(queue[0]["documents"]) == 3
    doc_id = queue[0]["documents"][0]["id"]
    url = (await admin_c.get(f"/admin/kyc/documents/{doc_id}/url")).json()["url"]
    assert (await admin_c.get(url)).status_code == 200  # admin can open the private file
    assert (await c.get(url)).status_code == 403        # the user cannot
    uid = queue[0]["user"]["id"]
    assert (await admin_c.post(f"/admin/kyc/{uid}/landlord/approve", json={})).json()["status"] == "verified"


async def test_full_flow():
    async with client() as admin_c, client() as owner, client() as tenant, client() as t2, client() as t3:
        await make_admin(admin_c)
        await signup(owner, "Karim", "karim@example.com", "01711111111")
        await signup(tenant, "Sadia", "sadia@example.com", "01722222222")
        await signup(t2, "Tanvir", "tanvir@example.com", "01733333333")
        await signup(t3, "Rumana", "rumana@example.com", "01744444444")
        area = await area_id(owner)

        # Entire flat needs a verified landlord
        r = await owner.post("/rent", json=flat(area))
        assert r.status_code == 403 and r.json()["detail"]["code"] == "kyc_required"
        await become_landlord(owner, admin_c)
        r = await owner.post("/rent", json=flat(area))
        assert r.status_code == 201, r.text
        lid = r.json()["id"]

        # Public view: no private fields, contact details stripped from description
        public = (await tenant.get(f"/rent/{lid}")).json()
        assert public["private"] is None and public["unlocked"] is False
        assert "01712" not in public["description"] and "x@y.com" not in public["description"]
        assert "***" in public["description"]
        listing = (await tenant.get("/rent", params={"area_id": await area_id(tenant, "Mirpur")})).json()
        assert listing["total"] == 1 and listing["items"][0]["private"] is None

        # Unlock costs 1 diamond, shows address, opens chat
        r = await tenant.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})
        assert r.status_code == 201, r.text
        room_id = r.json()["room_id"]
        assert r.json()["listing"]["private"]["house_no"] == "14/B"
        assert (await tenant.get("/auth/me")).json()["balance"] == 4
        r = await tenant.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})
        assert r.status_code == 409
        assert (await owner.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})).json()["detail"]["code"] == "own_listing"

        # Chat
        r = await tenant.post(f"/chat/rooms/{room_id}/messages", json={"body": "ফ্ল্যাটটা কি খালি আছে?"})
        assert r.status_code == 201
        rooms = (await owner.get("/chat/rooms")).json()
        assert rooms[0]["unread"] == 1 and rooms[0]["i_am_owner"] is True
        await owner.post(f"/chat/rooms/{room_id}/messages", json={"body": "জি, খালি আছে"})
        hist = (await tenant.get(f"/chat/rooms/{room_id}/messages")).json()
        assert [m["body"] for m in hist] == ["ফ্ল্যাটটা কি খালি আছে?", "জি, খালি আছে"]
        assert (await t2.get(f"/chat/rooms/{room_id}/messages")).status_code == 403

        # Review only after unlock
        assert (await t2.post("/reviews", json={"listing_type": "rent", "listing_id": lid, "rating": 5})).status_code == 403
        assert (await tenant.post("/reviews", json={"listing_type": "rent", "listing_id": lid, "rating": 5})).status_code == 201

        # t2 and t3 unlock too, then 3 reports hide the post
        for c in (t2, t3):
            assert (await c.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})).status_code == 201
        for c in (tenant, t2):
            assert (await c.post("/reports", json={"listing_type": "rent", "listing_id": lid, "reason": "fake"})).status_code == 201
        assert (await tenant.post("/reports", json={"listing_type": "rent", "listing_id": lid, "reason": "fake"})).status_code == 409
        r = await t3.post("/reports", json={"listing_type": "rent", "listing_id": lid, "reason": "scam"})
        assert r.json()["hidden"] is True
        assert (await t2.get(f"/rent/{lid}")).status_code == 410

        # Admin confirms: all three unlockers refunded, owner warned
        reports = (await admin_c.get("/admin/reports")).json()
        assert reports[0]["unlockers"] == 3
        r = await admin_c.post(f"/admin/reports/rent/{lid}/confirm", json={"note": "fake photos"})
        assert r.json()["refunded"] == 3
        for c in (tenant, t2, t3):
            assert (await c.get("/auth/me")).json()["balance"] == 5
        logs = (await admin_c.get("/admin/audit-logs")).json()
        assert {"report_confirmed", "kyc_approved"} <= {l["action"] for l in logs}


async def test_wallet_topup_and_free_bonus():
    async with client() as admin_c, client() as u:
        await make_admin(admin_c)
        await signup(u, "Sadia", "sadia@example.com", "01722222222")
        r = await u.post("/wallet/topup", json={"method": "bkash", "package_key": "popular", "trx_id": "9gh7k2lq1p", "sender_number": "01722222222"})
        assert r.status_code == 201
        r = await u.post("/wallet/topup", json={"method": "bkash", "package_key": "popular", "trx_id": "9GH7K2LQ1P", "sender_number": "01722222222"})
        assert r.status_code == 409 and r.json()["detail"]["code"] == "trx_used"
        pid = (await admin_c.get("/admin/payments")).json()[0]["id"]
        assert (await admin_c.post(f"/admin/payments/{pid}/approve")).status_code == 200
        assert (await admin_c.post(f"/admin/payments/{pid}/approve")).status_code == 404  # no double credit
        w = (await u.get("/wallet")).json()
        assert w["paid_balance"] == 25 and w["bonus_balance"] == 5
        assert (await u.post("/wallet/free-request", json={"reason": "ছাত্র"})).json()["detail"]["code"] == "free_not_allowed"
        tx = (await u.get("/wallet/transactions")).json()
        assert [t["kind"] for t in tx] == ["purchase", "bonus"]


async def test_bonus_spent_first_and_insufficient_balance():
    async with client() as admin_c, client() as owner, client() as tenant:
        await make_admin(admin_c)
        await signup(owner, "Karim", "karim@example.com", "01711111111")
        await signup(tenant, "Sadia", "sadia@example.com", "01722222222")
        area = await area_id(owner)
        await admin_c.put("/admin/settings", json={"values": {"costs": {"rent": 6, "truck": 1, "sell": 1, "donate": 1, "cleaning": 1, "quote": 1}}})
        lid = (await owner.post("/rent", json=flat(area, type="sublet"))).json()["id"]
        r = await tenant.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})
        assert r.status_code == 402 and r.json()["detail"]["code"] == "insufficient_balance"
        assert (await tenant.get("/auth/me")).json()["balance"] == 5  # nothing charged


async def test_delete_soon_after_unlock_refunds():
    async with client() as owner, client() as tenant:
        await signup(owner, "Karim", "karim@example.com", "01711111111")
        await signup(tenant, "Sadia", "sadia@example.com", "01722222222")
        lid = (await owner.post("/rent", json=flat(await area_id(owner), type="sublet"))).json()["id"]
        await tenant.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})
        assert (await tenant.get("/auth/me")).json()["balance"] == 4
        r = await owner.delete(f"/rent/{lid}")
        assert r.json()["refunded"] == 1
        assert (await tenant.get("/auth/me")).json()["balance"] == 5


async def test_owner_confirms_already_rented():
    async with client() as owner, client() as tenant:
        await signup(owner, "Karim", "karim@example.com", "01711111111")
        await signup(tenant, "Sadia", "sadia@example.com", "01722222222")
        lid = (await owner.post("/rent", json=flat(await area_id(owner), type="sublet"))).json()["id"]
        await tenant.post("/unlocks", json={"listing_type": "rent", "listing_id": lid})
        await tenant.post("/reports", json={"listing_type": "rent", "listing_id": lid, "reason": "already_rented"})
        rid = (await owner.get("/reports/on-my-listings")).json()[0]["id"]
        assert (await owner.post(f"/reports/{rid}/owner-confirm-rented")).status_code == 200
        assert (await tenant.get("/auth/me")).json()["balance"] == 5
        assert (await owner.get(f"/rent/{lid}")).json()["status"] == "rented"


async def test_jobs_endpoint_needs_secret():
    async with client() as c:
        assert (await c.post("/internal/run-jobs")).status_code == 403
        r = await c.post("/internal/run-jobs", headers={"X-Job-Secret": "test-job-secret"})
        assert r.status_code == 200 and "expired_listings" in r.json()
