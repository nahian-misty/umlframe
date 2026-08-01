import pytest

from backend.services import auth_service
from backend.services.auth_service import (
    EmailAlreadyRegisteredError,
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
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
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
