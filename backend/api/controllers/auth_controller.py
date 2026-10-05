from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.models.requests import ChangePasswordRequest, LoginRequest, RegisterRequest
from backend.models.responses import TokenResponse, UserResponse
from backend.services import auth_service
from backend.services.auth_service import (
    EmailAlreadyRegisteredError,
    IncorrectPasswordError,
    InvalidCredentialsError,
)


def _to_token_response(user: User) -> TokenResponse:
    token = auth_service.create_access_token(user)
    return TokenResponse(access_token=token, user=UserResponse(id=user.id, email=user.email))


async def register(request: RegisterRequest, db: Session) -> TokenResponse:
    try:
        user = auth_service.register_user(db, request.email, request.password)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Registration failed") from exc
    return _to_token_response(user)


async def login(request: LoginRequest, db: Session) -> TokenResponse:
    try:
        user = auth_service.authenticate_user(db, request.email, request.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Login failed") from exc
    return _to_token_response(user)


async def logout(current_user: User) -> dict[str, str]:
    return {"status": "logged out"}


async def get_me(current_user: User) -> UserResponse:
    return UserResponse(id=current_user.id, email=current_user.email)


async def change_password(
    request: ChangePasswordRequest, current_user: User, db: Session
) -> TokenResponse:
    try:
        user = auth_service.change_password(
            db, current_user, request.current_password, request.new_password
        )
    except IncorrectPasswordError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Password change failed") from exc
    # Every older token is now invalid, so hand back a fresh one for this session.
    return _to_token_response(user)
