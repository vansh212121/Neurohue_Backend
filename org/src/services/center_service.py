import logging
from typing import Optional, Dict, Any
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timezone
from src.crud.region_crud import region_repository
from src.crud.center_crud import center_repository
from src.schemas.center_schema import (
    CenterCreate,
    CenterListResponse,
    CenterUpdate,
    CenterMoveRegion,
)
from src.schemas.user_schema import UserRole, UserPayload
from src.models.center_model import Center, CenterStatus

from src.core.exception_utils import raise_for_status
from src.core.exceptions import (
    ResourceNotFound,
    NotAuthorized,
    ValidationError,
    ResourceAlreadyExists,
)

logger = logging.getLogger(__name__)


class CenterService:
    """Handles all center-related business logic."""

    def __init__(self):
        """
        Initializes the CenterService.
        This version has no arguments, making it easy for FastAPI to use,
        while still allowing for dependency injection during tests.
        """
        self.region_repository = region_repository
        self.center_repository = center_repository
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def _check_authorization(
        self, *, db: AsyncSession, current_user: UserPayload, region_id: uuid.UUID
    ) -> None:
        """
        Validates if the current user has permission to modify content in a specific Region.
        - Admin: YES (Always)
        - Regional Manager: YES (Only if assigned to this region)
        - Others: NO
        """
        # 1. Admins bypass everything
        if current_user.role == UserRole.ADMIN:
            return

        # 2. Others must be Regional Managers
        if current_user.role != UserRole.REGIONAL_MANAGER:
            raise NotAuthorized("You do not have permission to manage centers.")

        # 3. Fetch the region to check ownership
        region = await self.region_repository.get(db=db, obj_id=region_id)

        raise_for_status(
            condition=(region is None),
            exception=ResourceNotFound,
            detail=f"Region {region_id} not found.",
            resource_type="Region",
        )

        # 4. The Critical Check: Does this RM own this Region?
        if region.regional_manager_id != current_user.id:
            raise NotAuthorized(f"You are not the manager of Region '{region.name}'.")

    async def get_by_id(
        self, *, db: AsyncSession, center_id: uuid.UUID, current_user: UserPayload
    ) -> Optional[Center]:

        center = await self.center_repository.get(db=db, obj_id=center_id)
        raise_for_status(
            condition=(center is None),
            exception=ResourceNotFound,
            detail=f"Center with id {center_id} not found.",
            resource_type="Center",
        )

        await self._check_authorization(
            current_user=current_user, region_id=center.region_id, db=db
        )

        return center

    async def get_all_centers(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> CenterListResponse:

        # Input validation
        if skip < 0:
            raise ValidationError("Skip parameter must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")

        # Delegate fetching to the repository
        centers, total = await self.center_repository.get_all(
            db=db,
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_by,
            order_desc=order_desc,
        )

        # Calculate pagination info
        page = (skip // limit) + 1
        total_pages = (total + limit - 1) // limit  # Ceiling division

        # Construct the response schema
        response = CenterListResponse(
            items=centers, total=total, page=page, pages=total_pages, size=limit
        )

        self._logger.info(
            f"Center list retrieved by {current_user.id}: {len(centers)} centers returned"
        )
        return response

    async def create_center(
        self, *, db: AsyncSession, current_user: UserPayload, center_data: CenterCreate
    ) -> Center:

        await self._check_authorization(
            db=db, current_user=current_user, region_id=center_data.region_id
        )

        existing_name = await self.center_repository.get_by_name(
            db=db, name=center_data.name
        )
        raise_for_status(
            condition=(existing_name is not None),
            exception=ResourceAlreadyExists,
            detail=f"Center with name {center_data.name} already exists",
            resource_type="Center",
        )

        exisiting_code = await self.center_repository.get_by_center_code(
            db=db, center_code=center_data.center_code
        )
        raise_for_status(
            condition=(exisiting_code is not None),
            exception=ResourceAlreadyExists,
            detail=f"Center with center_code {center_data.center_code} already exists",
            resource_type="Center",
        )

        exisiting_email = await self.center_repository.get_by_email(
            db=db, email=center_data.email
        )
        raise_for_status(
            condition=(exisiting_email is not None),
            exception=ResourceAlreadyExists,
            detail=f"Center with email {center_data.email} already exists",
            resource_type="Center",
        )

        center_dict = center_data.model_dump()

        # Set Timestamps
        now = datetime.now(timezone.utc)
        center_dict["created_at"] = now
        center_dict["updated_at"] = now

        center_to_create = Center(**center_dict)

        new_center = await self.center_repository.create(db=db, db_obj=center_to_create)

        return new_center

    async def update_center(
        self,
        *,
        db: AsyncSession,
        center_id: uuid.UUID,
        current_user: UserPayload,
        center_data: CenterUpdate,
    ) -> Center:

        center_to_update = await self.get_by_id(
            db=db, center_id=center_id, current_user=current_user
        )

        self._check_authorization(
            current_user=current_user, db=db, region_id=center_to_update.region_id
        )

        await self._validate_update_duplicates(db, center_id, center_data)

        update_dict = center_data.model_dump(exclude_unset=True, exclude_none=True)

        # Remove timestamp fields that should not be manually updated
        for ts_field in {"created_at", "updated_at"}:
            update_dict.pop(ts_field, None)

        updated_center = await self.center_repository.update(
            db=db,
            center=center_data,
            fields_to_update=update_dict,
        )

        self._logger.info(
            f"Center {center_id} updated by {current_user.id}",
            extra={
                "updated_center_id": center_id,
                "updater_id": current_user.id,
                "updated_fields": list(update_dict.keys()),
            },
        )
        return updated_center

    async def move_center_region(
        self,
        *,
        db: AsyncSession,
        center_id: uuid.UUID,
        move_data: CenterMoveRegion,
        current_user: UserPayload,
    ) -> Center:
        """
        Special case: User must own BOTH the old region AND the new region
        (or be Admin).
        """
        center = await self.get_by_id(
            db=db, current_user=current_user, center_id=center_id
        )

        # 1. Check Old Region Access
        await self._check_authorization(
            db=db, current_user=current_user, region_id=center.region_id
        )

        # 2. Check New Region Access (You can't move a center to a region you don't own!)
        await self._check_authorization(
            db=db, current_user=current_user, region_id=move_data.new_region_id
        )

        updated_center = await self.center_repository.update(
            db=db,
            center=center,
            fields_to_update={"region_id": move_data.new_region_id},
        )

        self._logger.info(
            f"Center {center_id} moved to region {move_data.new_region_id}"
        )
        return updated_center

    async def change_status(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        center_id: uuid.UUID,
        new_status: CenterStatus,
    ) -> Center:

        center_to_update = await self.get_by_id(
            db=db, center_id=center_id, current_user=current_user
        )

        self._check_authorization(
            current_user=current_user, db=db, region_id=center_to_update.region_id
        )

        raise_for_status(
            condition=(center_to_update.status == new_status),
            exception=ValidationError,
            detail=f"Center is already {new_status}!",
        )

        updated_center = await self.center_repository.update(
            db=db, center=center_to_update, fields_to_update={"status": new_status}
        )

        self._logger.info(
            f"Center {center_id} status changed to {new_status.value} by {current_user.id}"
        )
        return updated_center

    async def delete_center(
        self, *, db: AsyncSession, current_user: UserPayload, center_id: uuid.UUID
    ):
        center_to_delete = await self.get_by_id(
            db=db, current_user=current_user, center_id=center_id
        )

        await self._check_authorization(
            current_user=current_user, db=db, region_id=center_to_delete.region_id
        )

        # 3. Perform the deletion
        await self.center_repository.delete(db=db, obj_id=center_id)

        self._logger.warning(
            f"Center {center_id} permanently deleted by {current_user.id}",
            extra={
                "deleted_center_id": center_id,
                "deleter_id": current_user.id,
            },
        )
        return {"message": "Center has been successfully deleted!"}

    async def _validate_update_duplicates(
        self, db: AsyncSession, center_id: uuid.UUID, data: CenterUpdate
    ):
        """Helper to check collisions on update."""
        if data.center_code:
            existing = await self.center_repository.get_by_center_code(
                db=db, center_code=data.center_code
            )
            if existing and existing.id != center_id:
                raise ResourceAlreadyExists(f"Center code '{data.center_code}' taken.")

        if data.name:
            existing = await self.center_repository.get_by_name(db=db, name=data.name)
            if existing and existing.id != center_id:
                raise ResourceAlreadyExists(f"Center name '{data.name}' taken.")


center_service = CenterService()
