"""Removes phone numbers, emails and links from public text, so nobody can
skip the diamond unlock by writing contact details in a post."""
import re

_BN_DIGITS = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")

# Bangladeshi mobile numbers with optional +88/88 prefix and separators,
# written with English or Bangla digits.
_PHONE = re.compile(r"(?:\+?\s*8\s*8[\s\-.]*)?0\s*1[\s\-.]*[3-9](?:[\s\-.]*\d){8}")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_URL = re.compile(r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|bd|xyz|me|io|info)(?:/\S*)?\b", re.IGNORECASE)
_SOCIAL = re.compile(r"\b(?:whats\s*app|imo|viber|telegram|হোয়াটসঅ্যাপ|ইমু)\b[^\n]{0,20}", re.IGNORECASE)

MASK = "***"


def clean_public_text(text: str | None) -> str:
    if not text:
        return ""
    # Work on a copy with English digits so Bangla-digit numbers are caught too,
    # then cut the same character ranges out of the original text.
    normalized = text.translate(_BN_DIGITS)
    spans: list[tuple[int, int]] = []
    for pattern in (_PHONE, _EMAIL, _URL, _SOCIAL):
        spans.extend(m.span() for m in pattern.finditer(normalized))
    if not spans:
        return text
    spans.sort()
    out, last = [], 0
    for start, end in spans:
        if start < last:
            continue
        out.append(text[last:start])
        out.append(MASK)
        last = end
    out.append(text[last:])
    return "".join(out)
