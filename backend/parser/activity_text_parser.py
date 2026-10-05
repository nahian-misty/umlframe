from __future__ import annotations

import re
from difflib import get_close_matches

# Same OCR-noise-correction idiom as text_parser._OCR_FIXES, trimmed for
# activity labels: the ";" -> ":" swap is dropped here because an action label
# is free-form statement text where ";" is legitimate ("a += 1; b += 1"),
# unlike a class-compartment line where ";" is almost always a misread colon.
_OCR_FIXES: list[tuple[str, str]] = [
    ("—", "-"),  # em-dash
    ("–", "-"),  # en-dash
    ("·", "."),  # middle dot
]

_YES_TOKENS = {"yes", "y", "true", "t"}
_NO_TOKENS = {"no", "n", "false", "f"}

# How close an OCR'd guard must be to a known token to count as it ("ves" -> "yes").
_GUARD_MATCH_CUTOFF = 0.66


def normalize_label(text: str) -> str:
    """Clean an OCR'd action/decision label: fix common misreads, collapse
    whitespace (including newlines from multi-line OCR), and strip."""
    for wrong, right in _OCR_FIXES:
        text = text.replace(wrong, right)
    return re.sub(r"\s+", " ", text).strip()


def classify_guard(text: str) -> str:
    """Map an OCR'd edge guard label to a canonical "yes"/"no", or "" when it
    is neither (unreadable, or a non-boolean guard this v1 doesn't model).
    Punctuation OCR picks up from nearby lines is ignored, and a read that is one
    character off a known token ("ves", "yeS") still counts."""
    token = re.sub(r"[^a-z]", "", normalize_label(text).lower())
    if not token:
        return ""
    if token in _YES_TOKENS:
        return "yes"
    if token in _NO_TOKENS:
        return "no"
    match = get_close_matches(token, ["yes", "no"], n=1, cutoff=_GUARD_MATCH_CUTOFF)
    if not match:
        return ""
    return "yes" if match[0] in _YES_TOKENS else "no"
