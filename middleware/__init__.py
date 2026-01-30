"""
Middleware components for LEGO Train Controller API.

This package contains authentication and request processing middleware.
"""
from .auth import (
    api_key_header,
    verify_api_key,
    authenticate_request,
    require_api_key,
    AuthenticationError
)

__all__ = [
    "api_key_header",
    "verify_api_key",
    "authenticate_request",
    "require_api_key",
    "AuthenticationError"
]
