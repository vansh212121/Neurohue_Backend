from pydantic import BaseModel, Field


class TokenRefresh(BaseModel):
    """Schema for requesting a new token pair using a refresh token."""

    refresh_token: str = Field(..., description="A valid refresh token.")


class TokenResponse(BaseModel):
    """
    Defines the response model for a successful token request (e.g., login).
    """

    access_token: str = Field(..., description="The JWT access token.")
    refresh_token: str = Field(..., description="The JWT refresh token.")
    token_type: str = Field(
        "bearer", description="The type of token, typically 'bearer'."
    )
