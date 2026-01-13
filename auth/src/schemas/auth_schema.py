import re
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)
from src.core.exceptions import ValidationError


# ========= Password Management Schemas ===========
class UserPasswordChange(BaseModel):
    """Schema for changing password (authenticated users)."""

    current_password: str = Field(..., description="current password")
    new_password: str = Field(
        ...,
        min_length=6,
        max_length=30,
        description="Strong password",
        examples=["SecurePass123!"],
    )

    @field_validator("new_password")
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

    @model_validator(mode="after")
    def validate_new_password_is_different(self) -> "UserPasswordChange":
        if self.current_password == self.new_password:
            raise ValidationError("New password must be different from the current one")
        return self
