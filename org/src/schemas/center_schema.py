import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    ConfigDict,
    field_validator,
    model_validator,
)
from src.core.exceptions import ValidationError
from src.models.center_model import CenterStatus


# ======================================================
# BASE SCHEMA
# ======================================================
class CenterBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Name of the center",
        examples=["ABC Center"],
    )
    center_code: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Unique center code",
        examples=["C-001"],
    )
    street_address: str = Field(
        ...,
        min_length=2,
        max_length=400,
        description="Street address of the center",
    )
    city: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="City of the center",
    )
    state: Optional[str] = Field(
        None,
        min_length=2,
        max_length=60,
        description="State of the center",
    )
    zipcode: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="ZIP / postal code of the center",
    )
    phone_number: str = Field(
        ...,
        min_length=7,
        max_length=20,
        description="Phone number of the center",
    )
    email: EmailStr = Field(
        ...,
        description="Email address of the center",
    )
    gst_number: Optional[str] = Field(
        None,
        min_length=5,
        max_length=40,
        description="GST number of the center",
    )
    place_of_supply: Optional[str] = Field(
        None,
        min_length=2,
        max_length=60,
        description="Place of supply for GST",
    )
    gst_status: Optional[str] = Field(
        None,
        min_length=2,
        max_length=20,
        description="GST status of the center",
    )

    # ---------- string cleanup ----------
    @field_validator(
        "name",
        "center_code",
        "street_address",
        "city",
        "state",
        "zipcode",
        "gst_number",
        "place_of_supply",
        "gst_status",
        mode="before",
    )
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValidationError("Field cannot be empty or whitespace")
        return v

    # ---------- center code validation ----------
    @field_validator("center_code")
    @classmethod
    def validate_center_code(cls, v: str) -> str:
        v = v.upper()
        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValidationError(
                "center_code may contain only letters, numbers, hyphens, and underscores"
            )
        return v

    # ---------- phone validation ----------
    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValidationError("Invalid phone number format")
        return v

    # ---------- GST validation (basic) ----------
    @field_validator("gst_number")
    @classmethod
    def validate_gst(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[0-9A-Z]{10,20}$", v.upper()):
            raise ValidationError("Invalid GST number format")
        return v.upper()


# ======================================================
# CREATE
# ======================================================
class CenterCreate(CenterBase):
    """Schema for creating a center."""

    pass


# ======================================================
# UPDATE
# ======================================================
class CenterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=40)
    center_code: Optional[str] = Field(None, min_length=2, max_length=100)
    street_address: Optional[str] = Field(None, min_length=2, max_length=400)
    city: Optional[str] = Field(None, min_length=2, max_length=60)
    state: Optional[str] = Field(None, min_length=2, max_length=60)
    zipcode: Optional[str] = Field(None, min_length=3, max_length=20)
    phone_number: Optional[str] = Field(None, min_length=7, max_length=20)
    email: Optional[EmailStr] = None
    gst_number: Optional[str] = Field(None, min_length=5, max_length=40)
    place_of_supply: Optional[str] = Field(None, min_length=2, max_length=60)
    gst_status: Optional[str] = Field(None, min_length=2, max_length=20)

    # ---------- string cleanup ----------
    @field_validator(
        "name",
        "center_code",
        "street_address",
        "city",
        "state",
        "zipcode",
        "gst_number",
        "place_of_supply",
        "gst_status",
        mode="before",
    )
    @classmethod
    def clean_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = " ".join(v.strip().split())
        if not v:
            raise ValidationError("Field cannot be empty or whitespace")
        return v

    # ---------- center code validation ----------
    @field_validator("center_code")
    @classmethod
    def validate_center_code(cls, v: str) -> str:
        v = v.upper()
        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValidationError(
                "center_code may contain only letters, numbers, hyphens, and underscores"
            )
        return v

    # ---------- phone validation ----------
    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^[0-9+\-\s]{7,20}$", v):
            raise ValidationError("Invalid phone number format")
        return v

    # ---------- GST validation (basic) ----------
    @field_validator("gst_number")
    @classmethod
    def validate_gst(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[0-9A-Z]{10,20}$", v.upper()):
            raise ValidationError("Invalid GST number format")
        return v.upper()

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
class CenterResponse(CenterBase):
    """Center response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Center ID")
    region_id: uuid.UUID = Field(..., description="Region ID")
    status: CenterStatus = Field(..., description="Center status")
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ======================================================
# LIST RESPONSE
# ======================================================
class CenterListResponse(BaseModel):
    """Response for paginated center list."""

    items: List[CenterResponse] = Field(..., description="List of centers")
    total: int = Field(..., ge=0, description="Total number of centers")
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
class CenterSearchParams(BaseModel):
    """Parameters for searching centers."""

    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Search in name, center_code, state, city, zipcode, email, phone_number",
    )
    status: Optional[CenterStatus] = Field(None, description="Filter by center status")
    region_id: Optional[uuid.UUID] = Field(None, description="Filter by region ID")
    created_after: Optional[date] = Field(None)
    created_before: Optional[date] = Field(None)

    @field_validator("search")
    @classmethod
    def clean_search(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_date_range(self) -> "CenterSearchParams":
        if self.created_after and self.created_before:
            if self.created_after > self.created_before:
                raise ValidationError("created_after must be before created_before")
        return self


# ======================================================
# EXPORTS
# ======================================================

__all__ = [
    "CenterBase",
    "CenterCreate",
    "CenterUpdate",
    "CenterResponse",
    "CenterListResponse",
    "CenterSearchParams",
]
