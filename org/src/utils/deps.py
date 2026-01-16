import logging
import uuid
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import Depends, Request, Query
from fastapi.security import OAuth2PasswordBearer

from src.core.config import settings
from src.core.exceptions import (
    InvalidToken,
    RateLimitExceeded,
    NotAuthorized,
    TokenRevoked,
    TokenExpired,
)

from src.core.security import token_manager, TokenType
from src.schemas.user_schema import UserPayload, UserRole

from src.services.rate_limit_service import (
    RateLimitService,
    rate_limit_service as _rate_limit_singleton,
)

logger = logging.getLogger(__name__)

# OAuth2 scheme
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=(
        f"{settings.AUTH_SERVICE_URL}/login"
        if hasattr(settings, "AUTH_SERVICE_URL")
        else "login"
    ),
    description="JWT Access Token",
)


# ==== Service Providers ====
def get_rate_limit_service() -> RateLimitService:
    return _rate_limit_singleton


# ================== CORE AUTHENTICATION ==================
async def _authenticate_user_from_token(
    request: Request,
    token: str,
    rate_limit_svc: RateLimitService,
) -> UserPayload:
    """
    Validates token using the shared security module.
    Checks Redis for revocation automatically.
    """
    client_ip = request.client.host if request.client else "unknown"

    try:
        # 3. USE SECURITY MODULE: This checks Signature + Expiry + Redis Revocation
        payload = await token_manager.verify_token(
            token, expected_type=TokenType.ACCESS
        )

        user_id_str = payload.get("sub")
        role_str = payload.get("role")

        if user_id_str is None:
            raise InvalidToken(detail="Token subject (sub) is missing.")

        # 4. CONSTRUCT USER: No DB call, just mapping data
        user = UserPayload(
            id=uuid.UUID(user_id_str),
            role=UserRole(role_str) if role_str else UserRole.STAFF,
        )

        # Attach to request
        request.state.user = user
        request.state.user_id = str(user.id)
        return user

    except (InvalidToken, TokenRevoked, TokenExpired):
        # We record failed attempts for security
        await rate_limit_svc.record_failed_auth_attempt(client_ip)
        raise  # Re-raise the specific error so FastAPI returns correct 401/403

    except Exception as e:
        logger.error(f"Unexpected auth error: {e}")
        await rate_limit_svc.record_failed_auth_attempt(client_ip)
        raise InvalidToken(detail="Could not validate credentials")


async def get_current_user(
    request: Request,
    token: str = Depends(reusable_oauth2),
    rate_limit_svc: RateLimitService = Depends(get_rate_limit_service),
) -> UserPayload:
    """Primary authentication dependency."""
    return await _authenticate_user_from_token(request, token, rate_limit_svc)


# ================== RBAC (EXACT COPY) ==================
class RoleChecker:
    def __init__(self, required_role: UserRole):
        self.required_role = required_role

    def __call__(
        self, request: Request, current_user: UserPayload = Depends(get_current_user)
    ) -> UserPayload:
        if current_user.role.priority < self.required_role.priority:
            logger.warning(
                f"Insufficient privileges: {current_user.role} < {self.required_role}"
            )
            raise NotAuthorized(
                f"Insufficient privileges. Required: '{self.required_role.value}'"
            )
        return current_user


require_admin = RoleChecker(UserRole.ADMIN)
require_manager = RoleChecker(UserRole.REGIONAL_MANAGER)
require_cdc = RoleChecker(UserRole.CDC)
require_therapist = RoleChecker(UserRole.THERAPIST)
require_staff = RoleChecker(UserRole.STAFF)


# ================== RATE LIMITING (EXACT COPY) ==================
class RateLimitChecker:
    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        identifier_type: str = "ip",
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.identifier_type = identifier_type

    async def __call__(
        self,
        request: Request,
        rate_limit_svc: RateLimitService = Depends(get_rate_limit_service),
    ):
        if self.identifier_type == "user":
            user = getattr(request.state, "user", None)
            identifier = f"user:{user.id}" if user else f"ip:{request.client.host}"
        else:
            identifier = f"ip:{request.client.host}"

        if await rate_limit_svc.is_rate_limited(
            identifier, self.max_requests, self.window_seconds
        ):
            raise RateLimitExceeded(
                detail=f"Rate limit exceeded. Max {self.max_requests}/{self.window_seconds}s.",
                retry_after=self.window_seconds,
            )


rate_limit_api = RateLimitChecker(
    max_requests=35, window_seconds=60, identifier_type="user"
)


# ================== UTILS (EXACT COPY) ==================
class PaginationParams:
    def __init__(
        self,
        page: int = Query(1, ge=1),
        size: int = Query(20, ge=1, le=100),
    ):
        self.page = page
        self.size = size
        self.skip = (page - 1) * size
        self.limit = size


async def get_pagination_params(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


async def get_request_context(request: Request) -> dict:
    return {
        "path": request.url.path,
        "method": request.method,
        "user_id": getattr(request.state, "user_id", None),
    }


# ================== HEALTH CHECK ==================
async def get_health_status() -> Dict[str, Any]:
    """Health check dependency. Delegate to a service if checks are complex."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": getattr(settings, "APP_VERSION", "unknown"),
    }


# ================== REQUEST CONTEXT ==================
def _client_ip_from_headers(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    xri = request.headers.get("x-real-ip")
    if xri:
        return xri.strip()
    return request.client.host if request.client else "unknown"


async def get_request_context(request: Request) -> dict:
    """Extract common request context information."""
    return {
        "client_ip": getattr(request.state, "client_ip", None)
        or _client_ip_from_headers(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "path": request.url.path,
        "method": request.method,
        "request_id": getattr(request.state, "request_id", None),
        "user_id": getattr(request.state, "user_id", None),
    }
