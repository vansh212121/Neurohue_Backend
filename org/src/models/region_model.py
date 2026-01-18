import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func, Column, String, DateTime, Float
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
)
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from src.models.center_model import Center


class RegionStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class RegionBase(SQLModel):
    name: str = Field(sa_column=Column(String(80), nullable=False, index=True))
    region_code: str = Field(
        sa_column=Column(String(40), nullable=False, index=True, unique=True)
    )
    general_location_description: Optional[str] = Field(
        sa_column=Column(String(400), default=None)
    )
    primary_city: str = Field(sa_column=Column(String(60), nullable=False, index=True))
    state: str = Field(sa_column=Column(String(60), nullable=False, index=True))
    country: str = Field(sa_column=Column(String(60), nullable=False, index=True))
    latitude: Optional[float] = Field(sa_column=Column(Float, nullable=True))
    longitude: Optional[float] = Field(sa_column=Column(Float, nullable=True))
    status: RegionStatus = Field(
        sa_column=Column(SAEnum(RegionStatus), nullable=False, index=True),
        default=RegionStatus.ACTIVE,
    )


class Region(RegionBase, table=True):
    __tablename__ = "regions"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            server_default=func.gen_random_uuid(),
            primary_key=True,
            index=True,
            nullable=False,
        ),
    )

    regional_manager_id: Optional[uuid.UUID] = Field(index=True, default=None)

    centers: List["Center"] = Relationship(back_populates="region")

    # Timestamps
    created_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True), server_default=func.now(), nullable=False
        )
    )
    updated_at: datetime = Field(
        sa_column=Column(
            DateTime(timezone=True),
            server_default=func.now(),
            onupdate=func.now(),
            nullable=False,
        )
    )

    def __repr__(self):
        return f"<Region(id='{self.id}, name='{self.name}')>"
