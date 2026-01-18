import logging
from typing import Optional, Dict, Any
import uuid

from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime, timezone
from src.crud.region_crud import region_repository
from src.schemas.region_schema import (
    RegionCreate,
    RegionListResponse,
    RegionUpdate,
)
from src.schemas.user_schema import UserRole, UserPayload
from src.models.region_model import Region, RegionStatus

from src.core.exception_utils import raise_for_status
from src.core.exceptions import (
    ResourceNotFound,
    NotAuthorized,
    ValidationError,
    ResourceAlreadyExists,
)

logger = logging.getLogger(__name__)


class RegionService:
    """Handles all region-related business logic."""

    def __init__(self):
        """
        Initializes the RegionService.
        This version has no arguments, making it easy for FastAPI to use,
        while still allowing for dependency injection during tests.
        """
        self.region_repository = region_repository
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _check_authorization(self, *, current_user: UserPayload, action: str) -> None:
        """
        Central authorization check. An admin can do anything.
        A non-admin can only perform actions on their own account.

        Args:
            current_user: The user performing the action
            target_user: The user being acted upon
            action: Description of the action for error messages

        Raises:
            NotAuthorized: If user lacks permission for the action
        """
        # Users can only modify their own account
        # Admins have super powers
        if current_user.role == UserRole.ADMIN:
            return

        raise_for_status(
            condition=(current_user.role != UserRole.ADMIN),
            exception=NotAuthorized,
            detail=f"You are not authorized to {action} this region.",
        )

    async def get_region_by_id(
        self, *, db: AsyncSession, current_user: UserPayload, region_id: uuid.UUID
    ) -> Optional[Region]:

        region = await self.region_repository.get(db=db, obj_id=region_id)
        raise_for_status(
            condition=(region is None),
            exception=ResourceNotFound,
            detail=f"Region with id {region_id} not found.",
            resource_type="Region",
        )

        self._check_authorization(current_user=current_user, action="fetch")

        self._logger.debug(f"Region {region_id} retrieved by user {current_user.id}")
        return region

    async def get_all_regions(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        skip: int = 0,
        limit: int = 50,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> RegionListResponse:
        """
        Lists regoins with pagination and filtering.

        Args:
            db: Database session
            current_user: User making the request
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters to apply
            order_by: Field to order by
            order_desc: Whether to order in descending order

        Returns:
            UserListResponse: Paginated list of regions

        Raises:
            NotAuthorized: If user lacks permission to list regoins
            ValidationError: If pagination parameters are invalid
        """
        self._check_authorization(current_user=current_user, action="fetch")

        # Input validation
        if skip < 0:
            raise ValidationError("Skip parameter must be non-negative")
        if limit <= 0 or limit > 100:
            raise ValidationError("Limit must be between 1 and 100")

        # Delegate fetching to the repository
        regions, total = await self.region_repository.get_all(
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
        response = RegionListResponse(
            items=regions, total=total, page=page, pages=total_pages, size=limit
        )

        self._logger.info(
            f"Region list retrieved by {current_user.id}: {len(regions)} regions returned"
        )
        return response

    async def create_region(
        self, *, db: AsyncSession, current_user: UserPayload, region_data: RegionCreate
    ) -> Region:

        self._check_authorization(current_user=current_user, action="Create")

        existing_region = await self.region_repository.get_by_name(
            db=db, name=region_data.name
        )
        raise_for_status(
            condition=existing_region is not None,
            exception=ResourceAlreadyExists,
            detail=f"Region with name '{region_data.name}' already exists.",
            resource_type="Region",
        )

        existing_region_code = await self.region_repository.get_by_region_code(
            db=db, region_code=region_data.region_code
        )
        raise_for_status(
            condition=existing_region_code is not None,
            exception=ResourceAlreadyExists,
            detail=f"Region with region_code '{region_data.region_code}' already exists.",
            resource_type="Region",
        )

        region_dict = region_data.model_dump()

        # Set Timestamps
        now = datetime.now(timezone.utc)
        region_dict["created_at"] = now
        region_dict["updated_at"] = now

        region_to_create = Region(**region_dict)

        # 4. Delegate creation to the repository
        new_region = await self.region_repository.create(db=db, db_obj=region_to_create)

        return new_region

    async def update_region(
        self,
        *,
        db: AsyncSession,
        region_id: uuid.UUID,
        region_data: RegionUpdate,
        current_user: UserPayload,
    ) -> Region:

        self._check_authorization(current_user=current_user, action="Update")

        region_to_update = await self.get_region_by_id(
            db=db, current_user=current_user, region_id=region_id
        )

        await self._validate_region_update(
            db=db, region_id=region_id, region_data=region_data
        )

        update_dict = region_data.model_dump(exclude_unset=True, exclude_none=True)

        # Remove timestamp fields that should not be manually updated
        for ts_field in {"created_at", "updated_at"}:
            update_dict.pop(ts_field, None)

        updated_region = await self.region_repository.update(
            db=db,
            region=region_to_update,
            fields_to_update=update_dict,
        )

        self._logger.info(
            f"Region {region_id} updated by {current_user.id}",
            extra={
                "updated_region_id": region_id,
                "updater_id": current_user.id,
                "updated_fields": list(update_dict.keys()),
            },
        )
        return updated_region

    async def change_status(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        region_id: uuid.UUID,
        new_status: RegionStatus,
    ) -> Region:

        self._check_authorization(current_user=current_user, action="Update")

        region = await self.get_region_by_id(
            db=db, current_user=current_user, region_id=region_id
        )
        raise_for_status(
            condition=(region.status == new_status),
            exception=ValidationError,
            detail=f"Region is already {new_status}!"
        )

        updated_region = await self.region_repository.update(
            db=db, region=region, fields_to_update={"status": new_status}
        )

        self._logger.info(
            f"Region {region_id} status changed to {new_status.value} by {current_user.id}"
        )
        return updated_region

    async def assign_region(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        region_id: uuid.UUID,
        regional_manager_id: uuid.UUID,
    ) -> Region:

        self._check_authorization(current_user=current_user, action="Assign")

        region = await self.get_region_by_id(
            db=db, current_user=current_user, region_id=region_id
        )

        raise_for_status(
            condition=(region.regional_manager_id is not None),
            exception=ResourceAlreadyExists,
            detail=f"Region is already assigned! to user {region.regional_manager_id}",
            resource_type="Region",
        )

        assigned_region = await self.region_repository.update(
            db=db,
            region=region,
            fields_to_update={"regional_manager_id": regional_manager_id},
        )

        self._logger.info(
            f"Region {region_id} assigned to {regional_manager_id}",
        )
        return assigned_region

    async def remove_region_manager(
        self,
        *,
        db: AsyncSession,
        current_user: UserPayload,
        region_id: uuid.UUID,
    ) -> Region:

        self._check_authorization(current_user=current_user, action="Assign")

        region = await self.get_region_by_id(
            db=db, current_user=current_user, region_id=region_id
        )

        raise_for_status(
            condition=(region.regional_manager_id is None),
            exception=ResourceNotFound,
            detail=f"Region does not have any regional_manager assigned!",
            resource_type="Region",
        )

        assigned_region = await self.region_repository.update(
            db=db,
            region=region,
            fields_to_update={"regional_manager_id": None},
        )

        return assigned_region

    async def delete_region(
        self, *, db: AsyncSession, region_id: uuid.UUID, current_user: UserPayload
    ):

        self._check_authorization(current_user=current_user, action="Delete")

        region_to_delete = await self.get_region_by_id(
            db=db, current_user=current_user, region_id=region_id
        )

        # 3. Perform the deletion
        await self.region_repository.delete(db=db, obj_id=region_id)

        self._logger.warning(
            f"Region {region_id} permanently deleted by {current_user.id}",
            extra={
                "deleted_region_id": region_id,
                "deleter_id": current_user.id,
            },
        )
        return {"message": "Region has been successfully deleted!"}

    async def _validate_region_update(
        self, *, db: AsyncSession, region_id: uuid.UUID, region_data: RegionUpdate
    ) -> None:
        """
        Validates that updates to unique fields (name, code) do not collide
        with other existing regions.
        """
        # 1. Check Name Duplication
        if region_data.name is not None:
            existing_region = await self.region_repository.get_by_name(
                db=db, name=region_data.name
            )
            # CRITICAL: If found, make sure it is NOT the one we are currently editing
            if existing_region and existing_region.id != region_id:
                raise ResourceAlreadyExists(
                    detail=f"Region with name '{region_data.name}' already exists.",
                    resource_type="Region",
                )

        # 2. Check Code Duplication
        if region_data.region_code is not None:
            existing_code = await self.region_repository.get_by_region_code(
                db=db, region_code=region_data.region_code
            )
            if existing_code and existing_code.id != region_id:
                raise ResourceAlreadyExists(
                    detail=f"Region with code '{region_data.region_code}' already exists.",
                    resource_type="Region",
                )


region_service = RegionService()
