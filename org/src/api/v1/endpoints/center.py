import logging
import uuid
from fastapi import APIRouter, Depends, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.config import settings
from src.schemas.user_schema import (
    UserPayload,
)
from src.schemas.center_schema import (
    CenterCreate,
    CenterUpdate,
    CenterMoveRegion,
    CenterListResponse,
    CenterSearchParams,
    CenterResponse,
)
from src.models.center_model import CenterStatus
from src.db.session import get_session
from src.utils.deps import (
    get_current_user,
    rate_limit_api,
    require_admin,
    require_manager,
    PaginationParams,
    get_pagination_params,
)
from src.services.center_service import center_service
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Center"],
    prefix=f"{settings.API_V1_STR}/centers",
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=CenterListResponse,
    summary="Get all centers",
    description="Get a paginated and filterable lists of Centers",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def get_all_centers(
    *,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    search_params: CenterSearchParams = Depends(CenterSearchParams),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
):
    return await center_service.get_all_centers(
        db=db,
        current_user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=search_params.model_dump(exclude_none=True),
        order_by=order_by,
        order_desc=order_desc,
    )


@router.get(
    "/{center_id}",
    status_code=status.HTTP_200_OK,
    response_model=CenterResponse,
    summary="Get center profile",
    description="Get center information by it;s ID",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def get_center_by_id(
    *,
    center_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await center_service.get_by_id(
        db=db, current_user=current_user, center_id=center_id
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CenterResponse,
    summary="Create a center",
    description="Create a center",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def create_center(
    *,
    center_data: CenterCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):
    return await center_service.create_center(
        db=db, center_data=center_data, current_user=current_user
    )


@router.patch(
    "/{center_id}/update",
    status_code=status.HTTP_200_OK,
    response_model=CenterResponse,
    summary="Update a center",
    description="Update a center by it's ID",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def update_center(
    *,
    center_id: uuid.UUID,
    center_data: CenterUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await center_service.update_center(
        db=db, current_user=current_user, center_data=center_data, center_id=center_id
    )


@router.patch(
    "/{center_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=CenterResponse,
    summary="Change status of a center",
    description="Change status of a center by it's ID",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def change_status(
    *,
    center_id: uuid.UUID,
    new_status: CenterStatus,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await center_service.change_status(
        db=db, current_user=current_user, new_status=new_status, center_id=center_id
    )


@router.patch(
    "/{center_id}/move-region",
    status_code=status.HTTP_200_OK,
    response_model=CenterResponse,
    summary="Change region of a center",
    description="Change region of a center by it's ID",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def move_region(
    *,
    center_id: uuid.UUID,
    center_data: CenterMoveRegion,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await center_service.move_center_region(
        db=db, current_user=current_user, center_id=center_id, move_data=center_data
    )


@router.delete(
    "/{center_id}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, str],
    summary="delete a center",
    description="delete a center",
    dependencies=[Depends(rate_limit_api), Depends(require_manager)],
)
async def delete_center(
    *,
    center_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    await center_service.delete_center(
        db=db, current_user=current_user, center_id=center_id
    )

    return {"message": "Center Deleted Successfully!"}
