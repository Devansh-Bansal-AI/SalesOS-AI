# ============================================================
# SalesOS AI — Auth Routes
# ============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_current_user
from app.db.session import get_db
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfile,
)
from app.schemas.common import APIResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=APIResponse[RegisterResponse], status_code=201)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new organization and admin user."""
    service = AuthService(db)
    result = await service.register(request)
    return APIResponse(data=result)


@router.post("/login", response_model=APIResponse[LoginResponse])
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password."""
    service = AuthService(db)
    result = await service.login(request)
    return APIResponse(data=result)


@router.post("/refresh", response_model=APIResponse[TokenResponse])
async def refresh(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token."""
    service = AuthService(db)
    result = await service.refresh_tokens(request.refresh_token)
    return APIResponse(data=result)


@router.get("/me", response_model=APIResponse[UserProfile])
async def me(
    user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    service = AuthService(db)
    profile = await service.get_profile(user.id)
    return APIResponse(data=profile)
