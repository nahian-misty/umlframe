from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from backend.config import settings
from backend.services import auth_service
from backend.services.auth_service import (
    EmailAlreadyRegisteredError,
    IncorrectPasswordError,
    InvalidCredentialsError,
    InvalidTokenError,
    UserNotFoundError,
)


def test_register_user_creates_user_with_hashed_password(db_session):
    user = auth_service.register_user(db_session, "alice@example.com", "password123")
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.hashed_password != "password123"


def test_register_duplicate_email_raises(db_session):
    auth_service.register_user(db_session, "alice@example.com", "password123")
    with pytest.raises(EmailAlreadyRegisteredError):
        auth_service.register_user(db_session, "alice@example.com", "different-password")


def test_authenticate_user_success(db_session):
    auth_service.register_user(db_session, "bob@example.com", "password123")
    user = auth_service.authenticate_user(db_session, "bob@example.com", "password123")
    assert user.email == "bob@example.com"


def test_authenticate_user_wrong_password_raises(db_session):
    auth_service.register_user(db_session, "bob@example.com", "password123")
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, "bob@example.com", "wrong-password")


def test_authenticate_unknown_email_raises(db_session):
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, "nobody@example.com", "password123")


def test_token_round_trip(db_session):
    user = auth_service.register_user(db_session, "carol@example.com", "password123")
    token = auth_service.create_access_token(user)
    assert auth_service.decode_access_token(token) == user.id


def test_decode_invalid_token_raises():
    with pytest.raises(InvalidTokenError):
        auth_service.decode_access_token("not-a-real-token")


def test_decode_tampered_token_raises(db_session):
    user = auth_service.register_user(db_session, "dave@example.com", "password123")
    token = auth_service.create_access_token(user)
    # Flip the second-to-last character rather than the last: the final base64url
    # character of a 32-byte HMAC-SHA256 signature carries 2 padding bits that
    # decoders ignore, so tampering it can occasionally be a no-op on the decoded
    # signature bytes and leave the token valid.
    tampered = token[:-2] + ("a" if token[-2] != "a" else "b") + token[-1]
    with pytest.raises(InvalidTokenError):
        auth_service.decode_access_token(tampered)


def test_get_user_by_id_success(db_session):
    user = auth_service.register_user(db_session, "erin@example.com", "password123")
    fetched = auth_service.get_user_by_id(db_session, user.id)
    assert fetched.email == "erin@example.com"


def test_get_user_by_id_not_found_raises(db_session):
    with pytest.raises(UserNotFoundError):
        auth_service.get_user_by_id(db_session, 999999)


def test_password_never_stored_in_plaintext(db_session):
    user = auth_service.register_user(db_session, "frank@example.com", "supersecret1")
    assert "supersecret1" not in user.hashed_password


def _token_issued_seconds_ago(user, seconds: int) -> str:
    issued = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    payload = {"sub": str(user.id), "iat": issued, "exp": issued + timedelta(hours=1)}
    return pyjwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def test_change_password_replaces_the_hash_and_login_uses_the_new_one(db_session):
    user = auth_service.register_user(db_session, "alice@example.com", "old-password-1")
    old_hash = user.hashed_password
    auth_service.change_password(db_session, user, "old-password-1", "new-password-2")

    assert user.hashed_password != old_hash
    assert auth_service.authenticate_user(db_session, "alice@example.com", "new-password-2")
    with pytest.raises(InvalidCredentialsError):
        auth_service.authenticate_user(db_session, "alice@example.com", "old-password-1")


def test_change_password_with_wrong_current_password_changes_nothing(db_session):
    user = auth_service.register_user(db_session, "alice@example.com", "old-password-1")
    old_hash = user.hashed_password
    with pytest.raises(IncorrectPasswordError):
        auth_service.change_password(db_session, user, "not-my-password", "new-password-2")
    assert user.hashed_password == old_hash
    assert user.password_changed_at is None


def test_change_password_rejects_reusing_the_current_password(db_session):
    user = auth_service.register_user(db_session, "alice@example.com", "old-password-1")
    with pytest.raises(ValueError, match="different"):
        auth_service.change_password(db_session, user, "old-password-1", "old-password-1")


def test_tokens_issued_before_a_password_change_are_rejected(db_session):
    user = auth_service.register_user(db_session, "alice@example.com", "old-password-1")
    old_token = _token_issued_seconds_ago(user, 30)
    assert auth_service.authenticate_token(db_session, old_token).id == user.id

    auth_service.change_password(db_session, user, "old-password-1", "new-password-2")

    with pytest.raises(InvalidTokenError):
        auth_service.authenticate_token(db_session, old_token)
    fresh_token = auth_service.create_access_token(user)
    assert auth_service.authenticate_token(db_session, fresh_token).id == user.id


def test_authenticate_token_rejects_garbage_and_unknown_users(db_session):
    with pytest.raises(InvalidTokenError):
        auth_service.authenticate_token(db_session, "garbage")
    ghost = auth_service.register_user(db_session, "ghost@example.com", "password123")
    token = auth_service.create_access_token(ghost)
    db_session.delete(ghost)
    db_session.commit()
    with pytest.raises(UserNotFoundError):
        auth_service.authenticate_token(db_session, token)
