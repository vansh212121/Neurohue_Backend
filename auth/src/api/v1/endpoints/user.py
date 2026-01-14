import logging
from fastapi import APIRouter, Depends, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.config import settings
from src.schemas.user_schema import (
    UserResponse,
    UserUpdateProfile,
)
from src.schemas.auth_schema import UserPasswordChange
from src.models.user_model import User
from src.db.session import get_session
from src.utils.deps import (
    get_current_user,
    rate_limit_api,
    rate_limit_auth,
)
from src.services.user_service import user_service
from src.services.auth_service import auth_service
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["User"],
    prefix=f"{settings.API_V1_STR}/users",
)


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Get current user profile",
    description="Get profile information for the authenticated user",
    dependencies=[Depends(rate_limit_api)],
)
async def get_my_profile(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.patch(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update profile information for the authenticated user",
    dependencies=[Depends(rate_limit_api)],
)
async def update_my_profile(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    user_data: UserUpdateProfile,
):
    updated_user = await user_service.update_user_profile(
        db=db,
        user_id_to_update=current_user.id,
        user_data=user_data,
        current_user=current_user,
    )

    return updated_user


@router.post(
    "/change-password",
    response_model=Dict[str, str],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Change Current User's Password",
    description="Change Current User's Password",
    dependencies=[Depends(rate_limit_auth)],
)
async def change_my_password(
    *,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
    password_data: UserPasswordChange,
):
    """Change a logged-in User Password"""
    await auth_service.change_password(
        db=db, password_data=password_data, user=current_user
    )

    return {"message": "Password updated successfully"}
