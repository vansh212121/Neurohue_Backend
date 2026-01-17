import logging
import uuid
from fastapi import APIRouter, Depends, status, Query
from sqlmodel.ext.asyncio.session import AsyncSession
from src.core.config import settings
from src.schemas.user_schema import (
    UserPayload,
)
from src.schemas.region_schema import (
    RegionCreate,
    RegionUpdate,
    RegionListResponse,
    RegionSearchParams,
    RegionResponse,
)
from src.models.region_model import RegionStatus
from src.db.session import get_session
from src.utils.deps import (
    get_current_user,
    rate_limit_api,
    require_admin,
    PaginationParams,
    get_pagination_params,
)
from src.services.region_service import region_service
from typing import Dict

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Region"],
    prefix=f"{settings.API_V1_STR}/regions",
)


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=RegionListResponse,
    summary="Get all regions",
    description="Get a paginated and filterable lists of Regions",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def get_all_regions(
    *,
    current_user: UserPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
    pagination: PaginationParams = Depends(get_pagination_params),
    search_params: RegionSearchParams = Depends(RegionSearchParams),
    order_by: str = Query("created_at", description="Field to order by"),
    order_desc: bool = Query(True, description="Order descending"),
):
    return await region_service.get_all_regions(
        db=db,
        current_user=current_user,
        skip=pagination.skip,
        limit=pagination.limit,
        filters=search_params.model_dump(exclude_none=True),
        order_by=order_by,
        order_desc=order_desc,
    )


@router.get(
    "/{region_id}",
    status_code=status.HTTP_200_OK,
    response_model=RegionResponse,
    summary="Get region  profile",
    description="Get region information by it;s ID",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def get_region_by_id(
    *,
    region_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await region_service.get_region_by_id(
        db=db, current_user=current_user, region_id=region_id
    )


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=RegionResponse,
    summary="Create a region",
    description="Create a region(admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def create_region(
    *,
    region_data: RegionCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):
    return await region_service.create_region(
        db=db, region_data=region_data, current_user=current_user
    )


@router.patch(
    "/{region_id}/update",
    status_code=status.HTTP_200_OK,
    response_model=RegionResponse,
    summary="Update a region",
    description="Update a region by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def update_region(
    *,
    region_id: uuid.UUID,
    region_data: RegionUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await region_service.update_region(
        db=db, current_user=current_user, region_data=region_data, region_id=region_id
    )


@router.patch(
    "/{region_id}/status",
    status_code=status.HTTP_200_OK,
    response_model=RegionResponse,
    summary="Change status of a region",
    description="Change status of a region by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def change_status(
    *,
    region_id: uuid.UUID,
    new_status: RegionStatus,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await region_service.change_status(
        db=db, current_user=current_user, new_status=new_status, region_id=region_id
    )


@router.patch(
    "/{region_id}/assign/{regional_manager_id}",
    status_code=status.HTTP_200_OK,
    response_model=RegionResponse,
    summary="Assign a region",
    description="Assign a region by it's ID (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def assign_region(
    *,
    region_id: uuid.UUID,
    regional_manager_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await region_service.assign_region(
        db=db,
        current_user=current_user,
        region_id=region_id,
        regional_manager_id=regional_manager_id,
    )


@router.delete(
    "/{region_id}/manager",
    status_code=status.HTTP_200_OK,
    response_model=RegionResponse,
    summary="remove a manager from region",
    description="remove a manager from region (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def remove_manager_region(
    *,
    region_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    return await region_service.remove_region_manager(
        db=db,
        current_user=current_user,
        region_id=region_id,
    )


@router.delete(
    "/{region_id}",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, str],
    summary="delete a region",
    description="delete a region region (admin only)",
    dependencies=[Depends(rate_limit_api), Depends(require_admin)],
)
async def delete_region(
    *,
    region_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    current_user: UserPayload = Depends(get_current_user),
):

    await region_service.delete_region(
        db=db, current_user=current_user, region_id=region_id
    )

    return {"message": "Region Deleted Successfully!"}
