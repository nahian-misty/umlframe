from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.controllers import auth_controller
from backend.api.dependencies.auth import get_current_user
from backend.db.models import User
from backend.db.session import get_db
from backend.models.requests import LoginRequest, RegisterRequest
from backend.models.responses import TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return await auth_controller.register(request, db)


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    return await auth_controller.login(request, db)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    return await auth_controller.logout(current_user)


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return await auth_controller.get_me(current_user)
