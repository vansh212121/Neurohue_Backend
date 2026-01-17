import re
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    field_validator,
    model_validator,
)
from src.core.exceptions import ValidationError
from src.models.region_model import RegionStatus


# ======================================================
# BASE SCHEMA
# ======================================================
class RegionBase(BaseModel):
    name: str = Field(
        ...,
        min_length=2,
        max_length=80,
        description="Region name",
        examples=["South Kerala"],
    )
    region_code: str = Field(
        ...,
        min_length=2,
        max_length=40,
        description="Region code",
        examples=["SKL-01"],
    )
    general_location_description: Optional[str] = Field(
        None,
        min_length=2,
        max_length=400,
        description="General location description of the region",
    )
    primary_city: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Primary city of the region",
    )
    state: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="State of the region",
    )
    country: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Country of the region",
    )
    latitude: Optional[float] = Field(
        None,
        ge=-90,
        le=90,
        description="Latitude of the region center",
    )
    longitude: Optional[float] = Field(
        None,
        ge=-180,
        le=180,
        description="Longitude of the region center",
    )

    # ---------- string cleanup ----------
    @field_validator(
        "name",
        "general_location_description",
        "primary_city",
        "state",
        "country",
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

    # ---------- region code normalization ----------
    @field_validator("region_code")
    @classmethod
    def validate_region_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValidationError(
                "region_code may only contain letters, numbers, hyphens, and underscores"
            )
        return v

    # ---------- lat/long consistency ----------
    @model_validator(mode="after")
    def validate_coordinates(self) -> "RegionBase":
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValidationError(
                "Both latitude and longitude must be provided together"
            )
        return self


# ======================================================
# CREATE
# ======================================================


class RegionCreate(RegionBase):
    """Schema for creating a region."""

    pass


# ======================================================
# UPDATE
# ======================================================
class RegionUpdate(BaseModel):
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=80,
        description="Region name",
    )
    region_code: Optional[str] = Field(
        None,
        min_length=2,
        max_length=40,
        description="Region code",
    )
    general_location_description: Optional[str] = Field(
        None,
        min_length=2,
        max_length=400,
        description="Region general location",
    )
    primary_city: Optional[str] = Field(
        None,
        min_length=2,
        max_length=60,
        description="Primary city of the region",
    )
    state: Optional[str] = Field(
        None,
        min_length=2,
        max_length=60,
        description="State of the region",
    )
    country: Optional[str] = Field(
        None,
        min_length=2,
        max_length=60,
        description="Country of the region",
    )
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)

    # ---------- string cleanup ----------
    @field_validator(
        "name",
        "general_location_description",
        "primary_city",
        "state",
        "country",
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

    # ---------- region code normalization ----------
    @field_validator("region_code")
    @classmethod
    def validate_region_code(cls, v: str) -> str:
        v = v.strip().upper()
        if not re.match(r"^[A-Z0-9_-]+$", v):
            raise ValidationError(
                "region_code may only contain letters, numbers, hyphens, and underscores"
            )
        return v

    @model_validator(mode="before")
    @classmethod
    def validate_at_least_one_field(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure at least one field is provided for update."""
        if not any(v is not None for v in values.values()):
            raise ValidationError("At least one field must be provided for update")
        return values

    @model_validator(mode="after")
    def validate_coordinates(self) -> "RegionUpdate":
        if (self.latitude is None) ^ (self.longitude is None):
            raise ValidationError(
                "Both latitude and longitude must be provided together"
            )
        return self


# ======================================================
# RESPONSE
# ======================================================


class RegionResponse(RegionBase):
    """Region response schema."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="Region ID")
    regional_manager_id: Optional[uuid.UUID] = Field(
        None, description="Regional manager ID"
    )
    status: RegionStatus = Field(..., description="Region status")
    created_at: datetime = Field(..., description="Registration timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# ======================================================
# LIST RESPONSE
# ======================================================
class RegionListResponse(BaseModel):
    """Response for paginated region list."""

    items: List[RegionResponse] = Field(..., description="List of regions")
    total: int = Field(..., ge=0, description="Total number of regions")
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
class RegionSearchParams(BaseModel):
    """Parameters for searching regions."""

    search: Optional[str] = Field(
        None,
        min_length=1,
        max_length=100,
        description="Search in name, region_code, state, city, country",
    )
    status: Optional[RegionStatus] = Field(None, description="Filter by region status")
    regional_manager_id: Optional[uuid.UUID] = Field(
        None, description="Filter by regional manager ID"
    )
    created_after: Optional[date] = Field(
        None, description="Filter regions created after this date"
    )
    created_before: Optional[date] = Field(
        None, description="Filter regions created before this date"
    )

    @field_validator("search")
    @classmethod
    def clean_search(cls, v: Optional[str]) -> Optional[str]:
        return v.strip() if v else v

    @model_validator(mode="after")
    def validate_date_range(self) -> "RegionSearchParams":
        if self.created_after and self.created_before:
            if self.created_after > self.created_before:
                raise ValidationError("created_after must be before created_before")
        return self


# ======================================================
# EXPORTS
# ======================================================

__all__ = [
    "RegionBase",
    "RegionCreate",
    "RegionUpdate",
    "RegionResponse",
    "RegionListResponse",
    "RegionSearchParams",
]
