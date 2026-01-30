"""
Authentication middleware for LEGO Train Controller API.

Implements API key authentication with header-based validation.
"""
import logging
from typing import Optional
from fastapi import HTTPException, Request, status
from fastapi.security import APIKeyHeader
from config import get_settings

logger = logging.getLogger(__name__)

# API key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthenticationError(Exception):
    """Custom exception for authentication errors."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


async def verify_api_key(api_key: Optional[str] = None) -> bool:
    """
    Verify API key against configured keys.

    Args:
        api_key: API key from request header

    Returns:
        bool: True if valid, False otherwise

    Raises:
        HTTPException: If authentication is required but key is invalid
    """
    settings = get_settings()

    # If authentication is disabled, allow all requests
    if not settings.require_auth:
        logger.debug("Authentication disabled, allowing request")
        return True

    # Check if API key is provided
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Check if API key is valid
    if api_key not in settings.api_keys_list:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    logger.debug(f"API key validated successfully: {api_key[:8]}...")
    return True


async def authenticate_request(request: Request) -> bool:
    """
    Middleware function to authenticate incoming requests.

    Args:
        request: FastAPI request object

    Returns:
        bool: True if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    settings = get_settings()

    # Skip authentication if disabled
    if not settings.require_auth:
        return True

    # Get API key from header
    api_key = request.headers.get("X-API-Key")

    # Verify API key
    return await verify_api_key(api_key)


def get_api_key(request: Request) -> Optional[str]:
    """
    Extract API key from request headers.

    Args:
        request: FastAPI request object

    Returns:
        Optional[str]: API key if present, None otherwise
    """
    return request.headers.get("X-API-Key")


# Helper function for protected endpoints
async def require_api_key(api_key: Optional[str] = None) -> bool:
    """
    Dependency function for protected endpoints.

    Usage in FastAPI:
        @app.get("/protected")
        async def protected_endpoint(authenticated: bool = Depends(require_api_key)):
            return {"message": "Access granted"}

    Args:
        api_key: API key from header (automatically extracted)

    Returns:
        bool: True if authenticated

    Raises:
        HTTPException: If authentication fails
    """
    return await verify_api_key(api_key)
