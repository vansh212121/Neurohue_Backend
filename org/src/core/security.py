import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Union

from jose import jwt, JWTError

from src.core.config import settings
from src.core.exceptions import (
    InternalServerError,
    InvalidToken,
    TokenExpired,
    TokenRevoked,
    ValidationError,
    TokenTypeInvalid,
)
from src.db.redis_conn import redis_client


# --- Setup ---
logger = logging.getLogger(__name__)


# ---- Enums & Config ----
class TokenType(str, Enum):
    """Defines the types of tokens the system can issue."""

    ACCESS = "access"
    REFRESH = "refresh"


def _aud_list(aud: Union[str, List[str]]) -> Union[str, List[str]]:
    """Normalize audience to jose-acceptable type."""
    if isinstance(aud, str) and "," in aud:
        return [a.strip() for a in aud.split(",") if a.strip()]
    return aud


class SecurityConfig:
    """Validates and holds all security-related configurations."""

    JWT_SECRET_KEY: str = settings.JWT_SECRET
    JWT_ALGORITHM: str = getattr(settings, "JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        getattr(settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 15)
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(
        getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 7)
    )
    TOKEN_ISSUER: str = getattr(settings, "TOKEN_ISSUER", "my-app")
    TOKEN_AUDIENCE: Union[str, List[str]] = _aud_list(
        getattr(settings, "TOKEN_AUDIENCE", "my-app:users")
    )
    ENABLE_TOKEN_BLACKLIST: bool = bool(
        getattr(settings, "ENABLE_TOKEN_BLACKLIST", True)
    )
    REDIS_FAIL_SECURE: bool = bool(getattr(settings, "REDIS_FAIL_SECURE", True))
    JWT_LEEWAY_SECONDS: int = int(
        getattr(settings, "JWT_LEEWAY_SECONDS", 10)
    )  # clock skew leeway

    @classmethod
    def validate(cls) -> None:
        if not cls.JWT_SECRET_KEY or len(cls.JWT_SECRET_KEY) < 32:
            raise ValidationError(
                "JWT_SECRET_KEY must be configured and be at least 32 characters long."
            )


SecurityConfig.validate()


# ---- Token Management ----
class TokenManager:
    """Low-level token operations - creation, verification, revocation/blacklist."""

    config = SecurityConfig

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _ts(dt: datetime) -> int:
        return int(dt.timestamp())

    def _default_expiry(self, token_type: TokenType) -> timedelta:
        if token_type == TokenType.ACCESS:
            return timedelta(minutes=self.config.ACCESS_TOKEN_EXPIRE_MINUTES)
        if token_type == TokenType.REFRESH:
            return timedelta(days=self.config.REFRESH_TOKEN_EXPIRE_DAYS)
        return timedelta(hours=1)

    async def verify_token(
        self, token: str, expected_type: TokenType
    ) -> Dict[str, Any]:
        """Verify and decode a JWT; validate iss/aud/exp/nbf; check type and blacklist."""
        if not token:
            raise InvalidToken("Token cannot be empty.")

        try:
            payload = jwt.decode(
                token,
                self.config.JWT_SECRET_KEY,
                algorithms=[self.config.JWT_ALGORITHM],
                audience=self.config.TOKEN_AUDIENCE,
                issuer=self.config.TOKEN_ISSUER,
                options={"leeway": self.config.JWT_LEEWAY_SECONDS},
            )

            token_type = payload.get("type")
            if token_type != expected_type.value:
                raise TokenTypeInvalid(
                    f"Expected '{expected_type.value}' token, but got '{token_type}'.",
                    expected=expected_type.value,
                    received=token_type,
                )

            if self.config.ENABLE_TOKEN_BLACKLIST:
                jti = payload.get("jti")
                if not jti:
                    raise InvalidToken("Token is missing the required 'jti' claim.")
                if await self.is_token_revoked(jti):
                    raise TokenRevoked()

            return payload

        except jwt.ExpiredSignatureError:
            raise TokenExpired() from None

        # 2. Specifically catch other known JWT errors
        except JWTError as e:
            raise InvalidToken(f"Token signature or claims are invalid: {e}") from e

        # 3. Catch ANY other exception (like "Not enough segments", etc.)
        #    and wrap it in our standard InvalidToken error to prevent a 500.
        except Exception as e:
            logger.warning(f"Token decode failed with an unexpected error: {e}")
            raise InvalidToken("Token is invalid or malformed.") from e

    async def is_token_revoked(self, jti: str) -> bool:
        """Check if a token's JTI is blacklisted."""
        if not self.config.ENABLE_TOKEN_BLACKLIST:
            return False

        if redis_client is None:
            msg = "Revocation check failed (Redis down)"
            logger.error("Redis client is None in is_token_revoked.")
            if self.config.REDIS_FAIL_SECURE:
                # Fail-secure: reject tokens if we can't check revocation
                raise InternalServerError(msg)
            return False

        try:
            key = f"revoked_token:{jti}"
            exists = await redis_client.exists(key)
            return bool(exists)
        except Exception:
            logger.error(
                "Failed to check token revocation status in Redis.", exc_info=True
            )
            if self.config.REDIS_FAIL_SECURE:
                raise InternalServerError("Revocation check failed (Redis down)")
            return False


token_manager = TokenManager()
