"""Shared authentication utilities for API controllers."""

from fastapi import Depends, HTTPException, Header
from typing import Optional


def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract and verify Bearer token from Authorization header.
    
    Args:
        authorization: The Authorization header value
        
    Returns:
        The extracted token (without "Bearer " prefix)
        
    Raises:
        HTTPException: If token is missing or malformed
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid authorization header format")
    
    return parts[1]
