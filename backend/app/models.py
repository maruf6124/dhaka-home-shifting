"""Database tables (SQLAlchemy 2.0). Works on MySQL 8 and SQLite (tests).

Enum-like columns are plain strings; allowed values are listed in comments and
validated in the Pydantic schemas.
"""
from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, utcnow


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


# ---------------------------------------------------------------- users & auth
class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(190), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime)
    language: Mapped[str] = mapped_column(String(2), default="bn")  # bn | en
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    warnings: Mapped[int] = mapped_column(Integer, default=0)
    welcome_bonus_given: Mapped[bool] = mapped_column(Boolean, default=False)

    roles: Mapped[list["UserRole"]] = relationship(back_populates="user", lazy="selectin", cascade="all, delete-orphan")


class UserRole(TimestampMixin, Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))  # client | landlord | driver | cleaner | admin
    kyc_status: Mapped[str] = mapped_column(String(20), default="none")  # none | pending | verified | rejected
    review_note: Mapped[str | None] = mapped_column(String(500))

    user: Mapped[User] = relationship(back_populates="roles")


class KycDocument(Base):
    __tablename__ = "kyc_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    doc_type: Mapped[str] = mapped_column(String(40))  # nid_front | nid_back | utility_bill | driving_license | vehicle_reg | team_photo ...
    storage_key: Mapped[str] = mapped_column(String(300))  # cloudinary public_id or local path; never public
    content_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    delete_after: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class OtpCode(Base):
    __tablename__ = "otp_codes"
    __table_args__ = (Index("ix_otp_email_purpose", "email", "purpose"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(190))
    purpose: Mapped[str] = mapped_column(String(20))  # signup | login | reset
    code_hash: Mapped[str] = mapped_column(String(128))
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrustedDevice(Base):
    __tablename__ = "trusted_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True)
    user_agent: Mapped[str | None] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_used_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- places & listings
class Area(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_bn: Mapped[str] = mapped_column(String(80))
    name_en: Mapped[str] = mapped_column(String(80))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"))


class RentListing(TimestampMixin, Base):
    __tablename__ = "rent_listings"
    __table_args__ = (Index("ix_rent_status_area", "status", "area_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(20))  # entire_flat | sublet
    area_id: Mapped[int] = mapped_column(ForeignKey("areas.id"))
    title: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text, default="")
    rent: Mapped[int] = mapped_column(Integer)
    service_charge: Mapped[int] = mapped_column(Integer, default=0)
    advance_months: Mapped[int] = mapped_column(Integer, default=0)
    rooms: Mapped[int] = mapped_column(Integer)
    baths: Mapped[int] = mapped_column(Integer)
    size_sqft: Mapped[int | None] = mapped_column(Integer)
    floor: Mapped[int | None] = mapped_column(Integer)
    tenant_type: Mapped[str] = mapped_column(String(20), default="any")  # family | bachelor | female | any
    amenities: Mapped[list] = mapped_column(JSON, default=list)  # ["lift","gas","generator","parking"]
    available_from: Mapped[date | None] = mapped_column(Date)
    # private fields — only shown after unlock
    road_no: Mapped[str] = mapped_column(String(60))
    house_no: Mapped[str] = mapped_column(String(60))
    contact_phone: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="active")  # active | rented | expired | hidden | removed | deleted
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime)

    area: Mapped[Area] = relationship(lazy="joined")
    owner: Mapped[User] = relationship(lazy="joined")


class ListingImage(Base):
    __tablename__ = "listing_images"
    __table_args__ = (Index("ix_img_listing", "listing_type", "listing_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_type: Mapped[str] = mapped_column(String(20))
    listing_id: Mapped[int] = mapped_column(Integer)
    url: Mapped[str] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------- diamonds
class Wallet(Base):
    __tablename__ = "wallets"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    paid_balance: Mapped[int] = mapped_column(Integer, default=0)
    bonus_balance: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class DiamondTransaction(Base):
    """Append-only ledger. Never update or delete rows."""

    __tablename__ = "diamond_transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[int] = mapped_column(Integer)  # + credit / - debit
    paid_delta: Mapped[int] = mapped_column(Integer, default=0)
    bonus_delta: Mapped[int] = mapped_column(Integer, default=0)
    kind: Mapped[str] = mapped_column(String(20))  # purchase | bonus | gift | unlock | quote | refund | admin_adjust
    ref_type: Mapped[str | None] = mapped_column(String(30))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PaymentRequest(Base):
    __tablename__ = "payment_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    method: Mapped[str] = mapped_column(String(20))  # bkash | nagad | sslcommerz
    package_key: Mapped[str] = mapped_column(String(30))
    diamonds: Mapped[int] = mapped_column(Integer)
    amount_bdt: Mapped[int] = mapped_column(Integer)
    trx_id: Mapped[str] = mapped_column(String(40), unique=True)
    sender_number: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")


class FreeDiamondRequest(Base):
    __tablename__ = "free_diamond_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    reason: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_amount: Mapped[int | None] = mapped_column(Integer)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user: Mapped[User] = relationship(foreign_keys=[user_id], lazy="joined")


class Unlock(Base):
    __tablename__ = "unlocks"
    __table_args__ = (UniqueConstraint("user_id", "listing_type", "listing_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    listing_type: Mapped[str] = mapped_column(String(20))
    listing_id: Mapped[int] = mapped_column(Integer, index=True)
    cost: Mapped[int] = mapped_column(Integer)
    paid_part: Mapped[int] = mapped_column(Integer, default=0)
    bonus_part: Mapped[int] = mapped_column(Integer, default=0)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("chat_rooms.id"))
    refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    refund_reason: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- chat
class ChatRoom(Base):
    __tablename__ = "chat_rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_type: Mapped[str] = mapped_column(String(20))
    listing_id: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    participants: Mapped[list["ChatParticipant"]] = relationship(lazy="selectin", cascade="all, delete-orphan")


class ChatParticipant(Base):
    __tablename__ = "chat_participants"
    __table_args__ = (UniqueConstraint("room_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_emailed_at: Mapped[datetime | None] = mapped_column(DateTime)
    has_blocked: Mapped[bool] = mapped_column(Boolean, default=False)  # this user blocked the other side


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (Index("ix_msg_room_created", "room_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("chat_rooms.id", ondelete="CASCADE"))
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------- trust & safety
class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (UniqueConstraint("reporter_id", "listing_type", "listing_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    listing_type: Mapped[str] = mapped_column(String(20))
    listing_id: Mapped[int] = mapped_column(Integer, index=True)
    reason: Mapped[str] = mapped_column(String(30))  # fake | already_rented | scam | no_reply | abuse | other
    note: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | confirmed | dismissed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("reviewer_id", "listing_type", "listing_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    listing_type: Mapped[str] = mapped_column(String(20))
    listing_id: Mapped[int] = mapped_column(Integer)
    rating: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(500), default="")
    link: Mapped[str | None] = mapped_column(String(300))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict | list | int | str] = mapped_column(JSON)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[int | None] = mapped_column(Integer)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
