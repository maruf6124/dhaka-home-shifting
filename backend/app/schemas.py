from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

Lang = Literal["bn", "en"]
_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value.translate(_BN_DIGITS) if ch.isdigit())
    if digits.startswith("880"):
        digits = digits[2:]
    if len(digits) != 11 or not digits.startswith("01") or digits[2] not in "3456789":
        raise ValueError("invalid Bangladeshi mobile number")
    return digits


# ---------------------------------------------------------------- auth
class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str
    password: str = Field(min_length=8, max_length=128)
    language: Lang = "bn"

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return normalize_phone(v)


class EmailIn(BaseModel):
    email: EmailStr


class OtpVerifyIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ResendIn(BaseModel):
    email: EmailStr
    purpose: Literal["signup", "login", "reset"]


class ResetIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


class RoleOut(BaseModel):
    role: str
    kyc_status: str
    review_note: str | None = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str
    language: str
    email_verified: bool
    roles: list[RoleOut]
    is_admin: bool
    balance: int = 0
    paid_balance: int = 0
    bonus_balance: int = 0


class UserUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    language: Lang | None = None


# ---------------------------------------------------------------- listings
TenantType = Literal["family", "bachelor", "female", "any"]
RentType = Literal["entire_flat", "sublet"]
Amenity = Literal["lift", "gas", "generator", "parking", "cctv", "guard"]


class RentIn(BaseModel):
    type: RentType
    area_id: int
    title: str = Field(min_length=5, max_length=150)
    description: str = Field(default="", max_length=3000)
    rent: int = Field(gt=0, le=10_000_000)
    service_charge: int = Field(default=0, ge=0)
    advance_months: int = Field(default=0, ge=0, le=12)
    rooms: int = Field(ge=1, le=20)
    baths: int = Field(ge=0, le=20)
    size_sqft: int | None = Field(default=None, gt=0)
    floor: int | None = Field(default=None, ge=0, le=100)
    tenant_type: TenantType = "any"
    amenities: list[Amenity] = []
    available_from: date | None = None
    road_no: str = Field(min_length=1, max_length=60)
    house_no: str = Field(min_length=1, max_length=60)
    contact_phone: str
    images: list[str] = Field(default=[], max_length=8)

    @field_validator("contact_phone")
    @classmethod
    def check_contact_phone(cls, v: str) -> str:
        return normalize_phone(v)


class RentUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=5, max_length=150)
    description: str | None = Field(default=None, max_length=3000)
    rent: int | None = Field(default=None, gt=0)
    service_charge: int | None = Field(default=None, ge=0)
    advance_months: int | None = Field(default=None, ge=0, le=12)
    rooms: int | None = Field(default=None, ge=1, le=20)
    baths: int | None = Field(default=None, ge=0, le=20)
    size_sqft: int | None = None
    floor: int | None = None
    tenant_type: TenantType | None = None
    amenities: list[Amenity] | None = None
    available_from: date | None = None
    road_no: str | None = None
    house_no: str | None = None
    contact_phone: str | None = None
    images: list[str] | None = Field(default=None, max_length=8)

    @field_validator("contact_phone")
    @classmethod
    def check_phone_opt(cls, v):
        return normalize_phone(v) if v else v


class StatusIn(BaseModel):
    status: Literal["active", "rented"]


class UnlockIn(BaseModel):
    listing_type: Literal["rent"]
    listing_id: int


class ReportIn(BaseModel):
    listing_type: Literal["rent"]
    listing_id: int
    reason: Literal["fake", "already_rented", "scam", "no_reply", "abuse", "other"]
    note: str | None = Field(default=None, max_length=500)


class ReviewIn(BaseModel):
    listing_type: Literal["rent"]
    listing_id: int
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=500)


# ---------------------------------------------------------------- wallet
class TopupIn(BaseModel):
    method: Literal["bkash", "nagad"]
    package_key: str
    trx_id: str = Field(min_length=6, max_length=40)
    sender_number: str

    @field_validator("sender_number")
    @classmethod
    def check_sender_number(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("trx_id")
    @classmethod
    def check_trx(cls, v: str) -> str:
        v = v.strip().upper()
        if not v.isalnum():
            raise ValueError("TrxID must be letters and digits")
        return v


class FreeRequestIn(BaseModel):
    reason: str = Field(min_length=3, max_length=300)


# ---------------------------------------------------------------- chat
class MessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


# ---------------------------------------------------------------- admin
class ReviewDecisionIn(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class BonusApproveIn(BaseModel):
    amount: int = Field(ge=1, le=100)


class GiftIn(BaseModel):
    user: str = Field(description="email or mobile number")
    amount: int = Field(ge=1, le=1000)
    reason: str = Field(min_length=3, max_length=255)


class SettingsIn(BaseModel):
    values: dict


class NotificationOut(BaseModel):
    id: int
    type: str
    title: str
    body: str
    link: str | None
    is_read: bool
    created_at: datetime
