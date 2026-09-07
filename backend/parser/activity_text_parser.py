from __future__ import annotations

import re

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


def normalize_label(text: str) -> str:
    """Clean an OCR'd action/decision label: fix common misreads, collapse
    whitespace (including newlines from multi-line OCR), and strip."""
    for wrong, right in _OCR_FIXES:
        text = text.replace(wrong, right)
    return re.sub(r"\s+", " ", text).strip()


def classify_guard(text: str) -> str:
    """Map an OCR'd edge guard label to a canonical "yes"/"no", or "" when it
    is neither (unreadable, or a non-boolean guard this v1 doesn't model)."""
    token = normalize_label(text).lower().strip(".:;!?")
    if token in _YES_TOKENS:
        return "yes"
    if token in _NO_TOKENS:
        return "no"
    return ""
