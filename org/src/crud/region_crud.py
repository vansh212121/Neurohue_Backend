import logging
import uuid
from typing import Optional, List, Dict, Any, TypeVar, Generic, Tuple
from abc import ABC, abstractmethod
from datetime import datetime, timezone

from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select, func, and_, or_, delete

from src.core.exception_utils import handle_exceptions
from src.core.exceptions import InternalServerError

from src.models.region_model import Region

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository providing consistent interface for database operations."""

    def __init__(self, model: type[T]):
        self.model = model

    @abstractmethod
    async def get(self, db: AsyncSession, *, obj_id: Any) -> Optional[T]:
        """Get entity by its primary key."""
        pass

    @abstractmethod
    async def create(self, db: AsyncSession, *, obj_in: Any) -> T:
        """Create a new entity."""
        pass

    @abstractmethod
    async def update(self, db: AsyncSession, *, db_obj: T, obj_in: Any) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, db: AsyncSession, *, obj_id: Any) -> None:
        """Delete an entity by its primary key."""


class RegionRepository(BaseRepository[Region]):
    """Repository for all database operations related to the Region model."""

    def __init__(self):
        super().__init__(Region)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def get(self, *, db: AsyncSession, obj_id: uuid.UUID) -> Optional[Region]:
        statement = select(self.model).where(self.model.id == obj_id)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def get_by_name(self, *, db: AsyncSession, name: str) -> Optional[Region]:
        statement = select(self.model).where(self.model.name == name)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def get_by_region_code(
        self, *, db: AsyncSession, region_code: str
    ) -> Optional[Region]:
        statement = select(self.model).where(self.model.region_code == region_code)
        result = await db.execute(statement)
        return result.scalar_one_or_none()

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def get_all(
        self,
        *,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> Tuple[List[Region], int]:
        """Get multiple regions with filtering and pagination."""
        query = select(self.model)

        # Apply filters
        if filters:
            query = self._apply_filters(query, filters)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = (await db.execute(count_query)).scalar_one()

        # Apply ordering
        query = self._apply_ordering(query, order_by, order_desc)

        # Apply pagination
        paginated_query = query.offset(skip).limit(limit)
        result = await db.execute(paginated_query)
        regions = result.scalars().all()

        return regions, total

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def create(self, db: AsyncSession, *, db_obj: Region) -> Region:
        """Create a new region. Expects a pre-constructed Region model object."""
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        self._logger.info(f"Region created: {db_obj.id}")
        return db_obj

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def update(
        self, db: AsyncSession, *, region: Region, fields_to_update: Dict[str, Any]
    ):
        """Updates specific fields of a region object."""
        for field, value in fields_to_update.items():
            if field in {"created_at", "updated_at"} and isinstance(value, str):
                try:
                    value = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    value = datetime.now(timezone.utc)

            setattr(region, field, value)

        db.add(region)
        await db.commit()
        await db.refresh(region)

        self._logger.info(
            f"Region fields updated for {region.id}: {list(fields_to_update.keys())}"
        )
        return region

    @handle_exceptions(
        default_exception=InternalServerError,
        message="An unexpected database error occurred.",
    )
    async def delete(self, db: AsyncSession, *, obj_id: uuid.UUID) -> None:
        """Permanently delete a region by ID."""

        statement = delete(self.model).where(self.model.id == obj_id)
        await db.execute(statement)
        await db.commit()
        self._logger.info(f"Region hard deleted: {obj_id}")
        return

    def _apply_filters(self, query, filters: Dict[str, Any]):
        """Apply filters to query."""
        conditions = []

        if "status" in filters and filters["status"]:
            conditions.append(Region.status == filters["status"])

        if "regional_manager_id" in filters and filters["regional_manager_id"]:
            conditions.append(
                Region.regional_manager_id == filters["regional_manager_id"]
            )

        if "search" in filters and filters["search"]:
            search_term = f"%{filters['search']}%"
            conditions.append(
                or_(
                    Region.name.ilike(search_term),
                    Region.region_code.ilike(search_term),
                    Region.state.ilike(search_term),
                    Region.primary_city.ilike(search_term),
                    Region.country.ilike(search_term),
                )
            )

        if conditions:
            query = query.where(and_(*conditions))

        return query

    def _apply_ordering(self, query, order_by: str, order_desc: bool):
        """Apply ordering to query."""
        order_column = getattr(self.model, order_by, self.model.created_at)
        if order_desc:
            return query.order_by(order_column.desc())
        else:
            return query.order_by(order_column.asc())


region_repository = RegionRepository()
