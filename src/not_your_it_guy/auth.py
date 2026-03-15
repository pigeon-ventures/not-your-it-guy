"""Bearer token authentication dependency."""

from not_your_it_guy.logger.logger_provider import get_logger
import os

from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = get_logger()

_bearer = HTTPBearer(auto_error=False)


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> str:
    """Validate the Bearer token against the API_TOKEN env variable.

    Raises 401 if the header is missing or the token does not match.
    Returns the token on success.
    """
    expected = os.getenv("API_TOKEN")

    if not expected:
        logger.warning("API_TOKEN is not set — all requests are rejected")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server is not configured with an API token.",
        )

    if credentials is None or credentials.credentials != expected:
        logger.warning("Rejected request — invalid or missing Bearer token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("Auth passed")
    return credentials.credentials
