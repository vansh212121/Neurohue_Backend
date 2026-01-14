import logging
from fastapi import APIRouter, Depends, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
import uuid
from src.core.config import settings
from src.schemas.user_schema import (
    UserResponse,
    UserUpdateAdmin,
    UserSearchParams,
    UserListResponse,
)
from src.models.user_model import User
from src.db.session import get_session
from src.utils.deps import (
    get_current_user,
    rate_limit_api,
    require_admin,
    PaginationParams,
    get_pagination_params,
)
from src.services.user_service import user_service

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Admin"],
    prefix=f"{settings.API_V1_STR}/admin",
)


@router.get(
    "/",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all Users",
    description="Get a paginated and filterable lists of Users",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def get_all_user(
    *,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    search_params: UserSearchParams = Depends(UserSearchParams),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
):
    return await user_service.get_users(
        db=db,
        current_user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=search_params.model_dump(exclude_none=True),
        order_by=order_by,
        order_desc=order_desc,
    )


@router.get(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Get user by id",
    description="Get all information for the user by id (moderators and admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def get_user_by_id(
    *,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return await user_service.get_user_by_id(
        user_id=user_id, db=db, current_user=current_user
    )


@router.patch(
    "/{user_id}/update",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Update a user",
    description="Update a user by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def update_user(
    *,
    user_id: uuid.UUID,
    user_data: UserUpdateAdmin,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):

    return await user_service.update_user_admin(
        db=db, current_user=current_user, user_data=user_data, user_id_to_update=user_id
    )


@router.patch(
    "/{user_id}/activate",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Activate a user",
    description="Activate a user by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def activate(
    *,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    return await user_service.activate_user(
        db=db, current_user=current_user, user_id=user_id
    )


@router.patch(
    "/{user_id}/deactivate",
    status_code=status.HTTP_200_OK,
    response_model=UserResponse,
    summary="Deactivate a user",
    description="Deactivate a user by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def deactivate(
    *,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    return await user_service.deactivate_user(
        db=db, current_user=current_user, user_id=user_id
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    response_model=dict[str, str],
    summary="Delete a user",
    description="Permenantly Delete a user by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def delete_user(
    *,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):

    await user_service.delete_user(
        db=db, user_id_to_delete=user_id, current_user=current_user
    )

    return {"message": "User has been successfully deleted!"}
