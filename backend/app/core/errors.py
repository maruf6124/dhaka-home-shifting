"""Bilingual API errors.

Raise ``AppError("code")``; the handler answers with
``{"detail": {"code": ..., "message": ...}}`` in the language from the
``Accept-Language`` header (``bn`` or ``en``; Bangla by default).
"""
from fastapi import Request
from fastapi.responses import JSONResponse

MESSAGES: dict[str, tuple[str, str]] = {
    # code: (bangla, english)
    "not_authenticated": ("লগইন করুন", "Please log in"),
    "forbidden": ("এই কাজের অনুমতি নেই", "You are not allowed to do this"),
    "banned": ("আপনার অ্যাকাউন্ট বন্ধ করা হয়েছে", "Your account has been suspended"),
    "not_found": ("খুঁজে পাওয়া যায়নি", "Not found"),
    "email_taken": ("এই ইমেইলে আগেই অ্যাকাউন্ট আছে", "An account with this email already exists"),
    "phone_taken": ("এই মোবাইল নম্বরে আগেই অ্যাকাউন্ট আছে", "An account with this mobile number already exists"),
    "bad_credentials": ("ইমেইল বা পাসওয়ার্ড ভুল", "Wrong email or password"),
    "email_not_verified": ("আগে ইমেইল যাচাই করুন", "Please verify your email first"),
    "otp_invalid": ("কোড ভুল বা মেয়াদ শেষ", "The code is wrong or has expired"),
    "otp_locked": ("অনেকবার ভুল কোড — ১৫ মিনিট পরে চেষ্টা করুন", "Too many wrong codes — try again in 15 minutes"),
    "otp_too_many": ("অনেকবার কোড চাওয়া হয়েছে — কিছুক্ষণ পরে চেষ্টা করুন", "Too many codes requested — please wait"),
    "weak_password": ("পাসওয়ার্ড কমপক্ষে ৮ অক্ষরের হতে হবে", "Password must be at least 8 characters"),
    "insufficient_balance": ("যথেষ্ট ডায়মন্ড নেই", "Not enough diamonds"),
    "already_unlocked": ("আপনি আগেই আনলক করেছেন", "You have already unlocked this"),
    "own_listing": ("নিজের পোস্ট আনলক করা যায় না", "You cannot unlock your own post"),
    "listing_unavailable": ("পোস্টটি এখন সক্রিয় নেই", "This post is not active"),
    "kyc_required": ("এই কাজের জন্য ভেরিফাইড রোল লাগবে", "A verified role is required for this"),
    "trx_used": ("এই TrxID আগেই ব্যবহার হয়েছে", "This TrxID has already been used"),
    "bad_package": ("প্যাকেজটি পাওয়া যায়নি", "Package not found"),
    "free_not_allowed": ("ব্যালেন্স ০ হলে তবেই ফ্রি বোনাস চাওয়া যায়", "Free bonus can be requested only when your balance is 0"),
    "free_cooldown": ("ফ্রি বোনাস ৩০ দিনে একবার চাওয়া যায়", "Free bonus can be requested once every 30 days"),
    "free_pending": ("আগের রিকোয়েস্ট এখনো অপেক্ষায় আছে", "Your previous request is still pending"),
    "already_reported": ("আপনি আগেই রিপোর্ট করেছেন", "You have already reported this"),
    "unlock_required": ("আগে আনলক করতে হবে", "You need to unlock this first"),
    "already_reviewed": ("আপনি আগেই রিভিউ দিয়েছেন", "You have already reviewed this"),
    "refund_not_eligible": ("এখন ফেরত পাওয়ার শর্ত পূরণ হয়নি", "Not eligible for a refund yet"),
    "too_many_images": ("সর্বোচ্চ ৮টি ছবি দেওয়া যায়", "Up to 8 images are allowed"),
    "bad_file": ("শুধু jpg, png, webp বা pdf, সর্বোচ্চ ৫ MB", "Only jpg, png, webp or pdf up to 5 MB"),
    "blocked": ("এই চ্যাটে মেসেজ পাঠানো যাচ্ছে না", "You cannot send messages in this chat"),
    "invalid": ("তথ্য সঠিক নয়", "Invalid data"),
    "rate_limited": ("অনেকবার চেষ্টা করা হয়েছে — একটু পরে চেষ্টা করুন", "Too many attempts — please try again later"),
}


class AppError(Exception):
    def __init__(self, code: str, status_code: int = 400, extra: dict | None = None):
        self.code = code
        self.status_code = status_code
        self.extra = extra or {}


def pick_lang(request: Request) -> str:
    header = (request.headers.get("accept-language") or "").lower()
    return "en" if header.startswith("en") else "bn"


def message(code: str, lang: str) -> str:
    bn, en = MESSAGES.get(code, (code, code))
    return en if lang == "en" else bn


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    lang = pick_lang(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": message(exc.code, lang), **exc.extra}},
    )
