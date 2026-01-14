import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)
from src.core.exceptions import ValidationError
from src.models.user_model import UserRole, UserStatus


class UserBase(BaseModel):
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="User's full name",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    phone: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="User phone number",
    )
    user_code: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="User's Code",
    )
    department: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="User's Department",
    )

    # -------- string cleanup --------
    @field_validator("full_name")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValidationError("Field cannot be empty or whitespace")
        return v

    # -------- phone validation --------
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValidationError("Invalid phone number format")
        return v

    # -------- user_code normalization --------
    @field_validator("user_code")
    @classmethod
    def validate_user_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValidationError(
                "user_code may only contain letters, numbers, hyphens, and underscores"
            )
        return v


class UserCreate(UserBase):
    role: UserRole = Field(..., description="User role")
    password: str = Field(
        ...,
        min_length=6,
        max_length=30,
        description="Strong password",
        examples=["SecurePass123!"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValidationError("Password must contain at least one digit")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValidationError(
                "Password must contain at least one special character"
            )
        return v


class UserUpdateAdmin(BaseModel):
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="User's full name",
        examples=["John Doe"],
    )
    email: Optional[EmailStr] = Field(
        None,
        description="User's email address",
        examples=["user@example.com"],
    )
    phone: Optional[str] = Field(
        None,
        min_length=7,
        max_length=20,
        description="User phone number",
    )
    user_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=40,
        description="User's Code",
    )
    department: Optional[str] = Field(
        None,
        min_length=2,
        max_length=50,
        description="User's Department",
    )

    # -------- string cleanup --------
    @field_validator("full_name", "department")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValidationError("Field cannot be empty or whitespace")
        return v

    # -------- phone validation --------
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValidationError("Invalid phone number format")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure at least one field is provided for update."""
        if not any(v is not None for v in values.values()):
            raise ValidationError("At least one field must be provided for update")
        return values


class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="User's full name",
        examples=["John Doe"],
    )
    phone: Optional[str] = Field(
        None,
        min_length=7,
        max_length=20,
        description="User phone number",
    )

    # -------- string cleanup --------
    @field_validator("full_name")
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValidationError("Field cannot be empty or whitespace")
        return v

    # -------- phone validation --------
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValidationError("Invalid phone number format")
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure at least one field is provided for update."""
        if not any(v is not None for v in values.values()):
            raise ValidationError("At least one field must be provided for update")
        return values


# ======================================================
# RESPONSE
# ======================================================
class UserResponse(UserBase):
    """Basic user response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User's ID")
    role: UserRole = Field(..., description="User's Role")
    status: UserStatus = Field(..., description="User's Status")
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ======================================================
# LIST RESPONSE
# ======================================================
class UserListResponse(BaseModel):
    """Response for paginated user list."""

    items: List[UserResponse] = Field(..., description="List of users")
    total: int = Field(..., ge=0, description="Total number of users")
    page: int = Field(..., ge=1, description="Current page number")
    pages: int = Field(..., ge=0, description="Total number of pages")
    size: int = Field(..., ge=1, le=100, description="Number of items per page")

    @property
    def has_next(self) -> bool:
        return self.page < self.pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1


# ======================================================
# SEARCH PARAMS
# ======================================================
class UserSearchParams(BaseModel):
    """Parameters for searching users."""

    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Search in email, full_name, phone, department",
    )
    status: Optional[UserStatus] = Field(None, description="Filter by user status")
    role: Optional[UserRole] = Field(None, description="Filter by role")
    created_after: Optional[date] = Field(
        None, description="Filter users created after this date"
    )
    created_before: Optional[date] = Field(
        None, description="Filter users created before this date"
    )

    @field_validator("search")
    @classmethod
    def clean_search(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_date_range(self) -> "UserSearchParams":
        if self.created_after and self.created_before:
            if self.created_after > self.created_before:
                raise ValidationError("created_after must be before created_before")
        return self


__all__ = [
    "UserBase",
    "UserCreate",
    "UserUpdateAdmin",
    "UserUpdateProfile",
    "UserResponse",
    "UserListResponse",
    "UserSearchParams",
]
