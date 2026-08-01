from __future__ import annotations

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.db.models import User
from backend.db.session import get_db
from backend.services import auth_service

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = auth_service.decode_access_token(credentials.credentials)
        return auth_service.get_user_by_id(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc
