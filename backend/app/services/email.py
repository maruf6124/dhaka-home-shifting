"""Sending email through Gmail SMTP (free with an App Password).

Without SMTP settings the email is printed to the console, so the whole app
can be tried locally. Call ``send_email`` from a FastAPI BackgroundTask.
"""
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import get_settings

log = logging.getLogger("email")
settings = get_settings()

# Last emails sent in console mode (used by tests and local development).
OUTBOX: list[dict] = []

TEMPLATES = {
    "otp_signup": {
        "bn": ("আপনার যাচাই কোড: {code}", "ঢাকা হোম শিফটিং-এ স্বাগতম!\n\nআপনার ইমেইল যাচাই কোড: {code}\nকোডের মেয়াদ ১০ মিনিট। কাউকে এই কোড বলবেন না।"),
        "en": ("Your verification code: {code}", "Welcome to Dhaka Home Shifting!\n\nYour email verification code: {code}\nIt expires in 10 minutes. Never share this code."),
    },
    "otp_login": {
        "bn": ("নতুন ডিভাইস থেকে লগইন কোড: {code}", "নতুন ডিভাইস বা ব্রাউজার থেকে লগইনের চেষ্টা হয়েছে।\n\nআপনার লগইন কোড: {code}\nআপনি না হলে এখনই পাসওয়ার্ড বদলান।"),
        "en": ("Login code for a new device: {code}", "Someone is logging in from a new device or browser.\n\nYour login code: {code}\nIf this wasn't you, change your password now."),
    },
    "otp_reset": {
        "bn": ("পাসওয়ার্ড রিসেট কোড: {code}", "পাসওয়ার্ড রিসেট করতে এই কোড দিন: {code}\nকোডের মেয়াদ ১০ মিনিট।"),
        "en": ("Password reset code: {code}", "Use this code to reset your password: {code}\nIt expires in 10 minutes."),
    },
    "new_message": {
        "bn": ("নতুন মেসেজ: {sender}", "{sender} আপনাকে মেসেজ পাঠিয়েছেন:\n\n\"{preview}\"\n\nউত্তর দিন: {link}"),
        "en": ("New message from {sender}", "{sender} sent you a message:\n\n\"{preview}\"\n\nReply here: {link}"),
    },
}


def render(template: str, lang: str, **values) -> tuple[str, str]:
    subject, body = TEMPLATES[template]["en" if lang == "en" else "bn"]
    return subject.format(**values), body.format(**values)


def send_email(to: str, template: str, lang: str, **values) -> None:
    subject, body = render(template, lang, **values)
    if not settings.smtp_user:
        OUTBOX.append({"to": to, "template": template, "subject": subject, "body": body, **values})
        log.warning("EMAIL (console mode) to=%s subject=%s\n%s", to, subject, body)
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.email_from_name, settings.smtp_user))
    msg["To"] = to
    msg.set_content(body)
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)
    except Exception:  # email must never break the request
        log.exception("Failed to send email to %s", to)
