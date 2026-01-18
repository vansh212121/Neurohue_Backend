import uuid
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func, Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel, Relationship

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models.region_model import Region


class CenterStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CenterBase(SQLModel):
    name: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    center_code: str = Field(
        sa_column=Column(String(40), nullable=False, unique=True, index=True)
    )

    street_address: str = Field(sa_column=Column(String(400), nullable=False))
    city: str = Field(sa_column=Column(String(60), nullable=False, index=True))
    state: Optional[str] = Field(sa_column=Column(String(60), nullable=True))
    zip_code: str = Field(sa_column=Column(String(20), nullable=False))

    phone_number: str = Field(sa_column=Column(String(20), nullable=False))
    email: str = Field(sa_column=Column(String(100), nullable=False))

    # Business/Tax Fields
    gst_number: Optional[str] = Field(
        default=None, sa_column=Column(String(40), nullable=True)
    )
    place_of_supply: Optional[str] = Field(
        default=None, sa_column=Column(String(60), nullable=True)
    )
    gst_status: Optional[str] = Field(
        default=None, sa_column=Column(String(20), nullable=True)
    )

    status: CenterStatus = Field(
        sa_column=Column(SAEnum(CenterStatus), nullable=False, index=True),
        default=CenterStatus.ACTIVE,
    )


class Center(CenterBase, table=True):
    __tablename__ = "centers"

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

    # --- THE RELATIONSHIP ---
    # 1. The Physical Foreign Key
    region_id: uuid.UUID = Field(foreign_key="regions.id", nullable=False, index=True)

    # 2. The Relationship Object (Python side)
    region: "Region" = Relationship(back_populates="centers")

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
        return f"<Center(id='{self.id}', code='{self.center_code}')>"
