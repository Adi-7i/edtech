"""
Core Exception Classes

Custom exceptions for the application.
"""

from fastapi import HTTPException, status


class BadRequestException(HTTPException):
    """400 Bad Request"""
    def __init__(self, message: str = "Bad request"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )


class NotFoundException(HTTPException):
    """404 Not Found"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=message
        )


class UnauthorizedException(HTTPException):
    """401 Unauthorized"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message
        )


class ForbiddenException(HTTPException):
    """403 Forbidden"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )
