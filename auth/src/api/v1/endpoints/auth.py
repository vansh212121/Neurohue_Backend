import logging
from fastapi import APIRouter, Depends, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.config import settings
from src.schemas.user_schema import UserResponse, UserCreate
from src.schemas.token_schema import TokenResponse, TokenRefresh
from src.models.user_model import User
from src.db.session import get_session
from src.utils.deps import (
    get_current_user,
    rate_limit_auth,
    rate_limit_api,
    reusable_oauth2,
    require_cdc,
)
from src.services.user_service import user_service
from src.services.auth_service import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Auth"],
    prefix=f"{settings.API_V1_STR}/auth",
)


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
    summary="Create a user account",
    description="Create a user profile",
    dependencies=[Depends(rate_limit_auth), Depends(require_cdc)],
)
async def register_user(
    *,
    db: AsyncSession = Depends(get_session),
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
):
    """registeration User api"""

    user = await user_service.create_user(
        db=db, user_in=user_data, current_user=current_user
    )

    logger.info(
        f"New user registered",
        extra={
            "user_id": user.id,
            "email": user.email,
        },
    )

    return user


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Login for Access Token",
    description="Authenticate with email and password to receive JWT tokens.",
    dependencies=[Depends(rate_limit_auth)],
)
async def user_login(
    *,
    request: Request,
    db: AsyncSession = Depends(get_session),
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    """
    Standard user login. The 'username' field of the form should contain the user's email.
    """
    client_ip = request.client.host if request.client else "unknown"

    return await auth_service.login(
        db=db,
        email=form_data.username,
        password=form_data.password,
        client_ip=client_ip,
    )


# ===========Logout========
@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="User Logout",
)
async def logout_user(
    token: TokenRefresh,
    access_token: str = Depends(reusable_oauth2),
    current_user: User = Depends(get_current_user),
):
    """User Logout Api"""
    await auth_service.logout(
        access_token=access_token, refresh_token=token.refresh_token
    )
    return  # A 204 response has no body


@router.post(
    "/refresh",
    status_code=status.HTTP_200_OK,
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Get new access token using refresh token",
    dependencies=[Depends(rate_limit_api)],
)
async def rotate_tokens(
    *, token_data: TokenRefresh, db: AsyncSession = Depends(get_session)
):
    """
    Refresh access token using refresh token.

    The old refresh token will be revoked and a new token pair will be issued.
    This implements token rotation for enhanced security.
    """

    return await auth_service.refresh_token(
        db=db, refresh_token=token_data.refresh_token
    )
