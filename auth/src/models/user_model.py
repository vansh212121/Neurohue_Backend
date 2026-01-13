import uuid
from datetime import datetime
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func, Column, String, DateTime
from sqlalchemy.dialects.postgresql import (
    UUID as PG_UUID,
)
from sqlmodel import Field, SQLModel, Relationship


class UserRole(str, PyEnum):
    ADMIN = "admin"
    REGIONAL_MANAGER = "regional_manager"
    CDC = "cdc"
    THERAPIST = "therapist"
    STAFF = "staff"

    @property
    def priority(self) -> int:
        priorities = {
            self.STAFF: 2,
            self.THERAPIST: 2,
            self.CDC: 3,
            self.REGIONAL_MANAGER: 4,
            self.ADMIN: 5,
        }
        return priorities.get(self, 0)

    def __lt__(self, other: "UserRole") -> bool:
        if not isinstance(other, UserRole):
            return NotImplemented
        return self.priority < other.priority


class UserStatus(str, PyEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class UserBase(SQLModel):
    full_name: str = Field(
        sa_column=Column(
            String(100),
            nullable=False,
            index=True,
        )
    )
    email: str = Field(
        sa_column=Column(String(200), unique=True, nullable=False, index=True)
    )
    role: UserRole = Field(
        sa_column=Column(SAEnum(UserRole), nullable=False, index=True),
        default=UserRole.ADMIN,
    )
    phone: str = Field(sa_column=Column(String(20), nullable=False, index=True))
    status: UserStatus = Field(
        sa_column=Column(SAEnum(UserStatus), nullable=False, index=True),
        default=UserStatus.ACTIVE,
    )
    user_code: str = Field(sa_column=Column(String(40), nullable=False, index=True))
    department: Optional[str] = Field(
        sa_column=Column(String(50), default=None, index=True)
    )



class User(UserBase, table=True):
    __tablename__ = "users"

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
    
    hashed_password: str = Field(nullable=False, exclude=True)


    # Timestamps
    # created_At used as join date
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
    tokens_valid_from_utc: Optional[datetime] = Field(
        default=None, sa_column=Column(DateTime(timezone=True))
    )

    # --- Computed properties (data-focused) ---
    @property
    def is_admin(self) -> bool:
        return UserRole(self.role) == UserRole.ADMIN

    @property
    def is_manager(self) -> bool:
        return UserRole(self.role) == UserRole.REGIONAL_MANAGER

    @property
    def is_cdc(self) -> bool:
        return UserRole(self.role) == UserRole.CDC

    @property
    def is_therapist(self) -> bool:
        return UserRole(self.role) == UserRole.THERAPIST

    @property
    def is_staff(self) -> bool:
        return UserRole(self.role) == UserRole.STAFF

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', name='{self.full_name}')>"
