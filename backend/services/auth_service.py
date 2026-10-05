from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from sqlalchemy.orm import Session

from backend.config import settings
from backend.db.models import User


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InvalidTokenError(ValueError):
    pass


class UserNotFoundError(ValueError):
    pass


class IncorrectPasswordError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register_user(db: Session, email: str, password: str) -> User:
    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise EmailAlreadyRegisteredError(f"Email '{email}' is already registered")

    user = User(email=email, hashed_password=_hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user is None or not _verify_password(password, user.hashed_password):
        raise InvalidCredentialsError("Invalid email or password")
    return user


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode_payload(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Invalid or expired token") from exc


def decode_access_token(token: str) -> int:
    try:
        return int(_decode_payload(token)["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Invalid or expired token") from exc


def authenticate_token(db: Session, token: str) -> User:
    """The user a bearer token belongs to; a token issued before the user's last password
    change is rejected, so changing the password signs out every other session."""
    payload = _decode_payload(token)
    try:
        user_id = int(payload["sub"])
        issued_at = int(payload["iat"])
    except (KeyError, ValueError, TypeError) as exc:
        raise InvalidTokenError("Invalid or expired token") from exc

    user = get_user_by_id(db, user_id)
    if user.password_changed_at is not None:
        # iat has one-second resolution, so compare against the changed time floored to it
        changed_at = int(user.password_changed_at.replace(tzinfo=timezone.utc).timestamp())
        if issued_at < changed_at:
            raise InvalidTokenError("Invalid or expired token")
    return user


def change_password(db: Session, user: User, current_password: str, new_password: str) -> User:
    if not _verify_password(current_password, user.hashed_password):
        raise IncorrectPasswordError("Current password is incorrect")
    if current_password == new_password:
        raise ValueError("New password must be different from the current password")
    user.hashed_password = _hash_password(new_password)
    user.password_changed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise UserNotFoundError(f"User '{user_id}' not found")
    return user
