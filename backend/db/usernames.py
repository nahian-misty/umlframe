import re
from collections.abc import Container

MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 30
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+$")
FALLBACK_USERNAME = "user"
_DISALLOWED_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def derive_username(email: str, taken_lowercase: Container[str]) -> str:
    """A valid, unused username built from an email's local part (for accounts created
    before usernames existed, or a signup that did not pick one)."""
    base = _DISALLOWED_CHARS.sub("", email.split("@")[0])[:MAX_USERNAME_LENGTH]
    if len(base) < MIN_USERNAME_LENGTH:
        base = FALLBACK_USERNAME
    candidate, suffix = base, 1
    while candidate.lower() in taken_lowercase:
        suffix += 1
        tail = str(suffix)
        candidate = f"{base[: MAX_USERNAME_LENGTH - len(tail)]}{tail}"
    return candidate
