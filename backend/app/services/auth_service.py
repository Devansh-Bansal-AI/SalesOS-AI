# ============================================================
# SalesOS AI — Auth Service
# Business logic for authentication and registration.
# ============================================================

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_refresh_token,
)
from app.models.organization import Organization
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserProfile,
)

logger = get_logger("auth_service")


class AuthService:
    """Handles user authentication, registration, and token management."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.settings = get_settings()

    async def register(self, request: RegisterRequest) -> RegisterResponse:
        """Register a new organization and admin user."""
        # Check if email is already registered
        existing = await self.user_repo.find_by_email_any_org(request.email)
        if existing:
            raise ConflictError("A user with this email already exists")

        # Create organization
        from slugify import slugify
        slug = slugify(request.organization_name)

        # Ensure unique slug
        base_slug = slug
        counter = 1
        from app.repositories.base import BaseRepository
        org_repo = BaseRepository(Organization, self.session)
        while await org_repo.exists(slug=slug):
            slug = f"{base_slug}-{counter}"
            counter += 1

        org = Organization(
            name=request.organization_name,
            slug=slug,
        )
        self.session.add(org)
        await self.session.flush()

        # Create admin user
        user = User(
            organization_id=org.id,
            email=request.email,
            password_hash=hash_password(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
            role="admin",
        )
        self.session.add(user)
        await self.session.flush()

        # Generate tokens
        access_token = create_access_token(user.id, org.id, user.role)
        refresh_token = create_refresh_token(user.id, org.id)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        logger.info(
            "user_registered",
            user_id=str(user.id),
            org_id=str(org.id),
            email=request.email,
        )

        return RegisterResponse(
            user_id=user.id,
            organization_id=org.id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
        )

    async def login(self, request: LoginRequest) -> LoginResponse:
        """Authenticate user and return tokens."""
        user = await self.user_repo.find_by_email_any_org(request.email)
        if not user:
            raise AuthenticationError("Invalid email or password")

        if not verify_password(request.password, user.password_hash):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account is deactivated")

        # Update last login
        user.last_login_at = datetime.now(UTC)
        await self.session.flush()

        # Generate tokens
        access_token = create_access_token(user.id, user.organization_id, user.role)
        refresh_token = create_refresh_token(user.id, user.organization_id)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        logger.info("user_login", user_id=str(user.id), email=request.email)

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            user=UserProfile(
                id=user.id,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                organization_id=user.organization_id,
                organization_name=user.organization.name if user.organization else None,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                last_login_at=user.last_login_at,
                created_at=user.created_at,
            ),
        )

    async def refresh_tokens(self, refresh_token_str: str) -> TokenResponse:
        """Refresh access token using a valid refresh token."""
        payload = verify_refresh_token(refresh_token_str)

        user_id = UUID(payload["sub"])
        org_id = UUID(payload["org"])

        # Verify user still exists and is active
        user = await self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or deactivated")

        # Issue new token pair
        access_token = create_access_token(user.id, org_id, user.role)
        new_refresh_token = create_refresh_token(user.id, org_id)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=self.settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_at=expires_at,
        )

    async def get_profile(self, user_id: UUID) -> UserProfile:
        """Get the current user's profile."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User", user_id)

        return UserProfile(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role,
            organization_id=user.organization_id,
            organization_name=user.organization.name if user.organization else None,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
