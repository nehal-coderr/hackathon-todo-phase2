# Task ID: T028, T029 - JWT verification dependency
"""FastAPI dependencies for authentication.

Per Constitution Principle III: Security-First Design
- JWT verification on every API request
- user_id derived ONLY from JWT claims (never from request body/params)

Per FR-007: System MUST validate token on every protected request
Per FR-008: System MUST reject requests without valid token with appropriate error
Per FR-020: System MUST derive user identity solely from validated JWT token
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from src.config import settings

# HTTP Bearer security scheme
security = HTTPBearer()


class AuthenticationError(HTTPException):
    """Custom exception for authentication failures."""

    def __init__(self, detail: str = "Invalid or missing authentication token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "UNAUTHORIZED", "message": detail}},
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)]
) -> str:
    """
    Task ID: T029 - Extract and validate user_id from JWT.

    Per FR-020: user_id derived exclusively from JWT token
    Per research.md: Better Auth issues JWTs with 'sub' claim containing user_id

    Args:
        credentials: HTTP Authorization header with Bearer token

    Returns:
        str: The user_id extracted from the JWT 'sub' claim

    Raises:
        HTTPException: 401 if token is invalid, expired, or missing user_id
    """
    token = credentials.credentials

    try:
        # Decode and verify the JWT
        payload = jwt.decode(
            token,
            settings.BETTER_AUTH_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )

        # Extract user_id from 'sub' claim (standard JWT claim for subject)
        user_id: str | None = payload.get("sub")

        if user_id is None:
            raise AuthenticationError("Token missing user identifier")

        return user_id

    except JWTError as e:
        # Per FR-008: Reject with appropriate error
        raise AuthenticationError(f"Invalid token: {str(e)}")


# Type alias for dependency injection
CurrentUserId = Annotated[str, Depends(get_current_user_id)]
