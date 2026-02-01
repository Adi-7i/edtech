"""
Smart Study Planner - Global Exception Handlers

Centralized exception handling for consistent error responses.
Catches all exceptions and converts them to standard error format.
"""

from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.core.responses.base import error_response
from app.shared.constants import ResponseMessage, StatusCode


# -----------------------------------------------------------------------------
# Custom Exception Classes
# -----------------------------------------------------------------------------

class AppException(Exception):
    """
    Base application exception.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str = ResponseMessage.INTERNAL_ERROR,
        status_code: int = StatusCode.INTERNAL_SERVER_ERROR,
        errors: list = None,
    ):
        self.message = message
        self.status_code = status_code
        self.errors = errors or []
        super().__init__(self.message)


class NotFoundException(AppException):
    """Resource not found exception."""
    
    def __init__(self, message: str = ResponseMessage.NOT_FOUND):
        super().__init__(
            message=message,
            status_code=StatusCode.NOT_FOUND,
        )


class BadRequestException(AppException):
    """Bad request exception."""
    
    def __init__(self, message: str = ResponseMessage.BAD_REQUEST, errors: list = None):
        super().__init__(
            message=message,
            status_code=StatusCode.BAD_REQUEST,
            errors=errors,
        )


class UnauthorizedException(AppException):
    """Unauthorized exception."""
    
    def __init__(self, message: str = ResponseMessage.UNAUTHORIZED):
        super().__init__(
            message=message,
            status_code=StatusCode.UNAUTHORIZED,
        )


class ForbiddenException(AppException):
    """Forbidden exception."""
    
    def __init__(self, message: str = ResponseMessage.FORBIDDEN):
        super().__init__(
            message=message,
            status_code=StatusCode.FORBIDDEN,
        )


class ConflictException(AppException):
    """Conflict exception (e.g., duplicate resource)."""
    
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(
            message=message,
            status_code=StatusCode.CONFLICT,
        )


class ValidationException(AppException):
    """Validation exception."""
    
    def __init__(self, message: str = ResponseMessage.VALIDATION_ERROR, errors: list = None):
        super().__init__(
            message=message,
            status_code=StatusCode.UNPROCESSABLE_ENTITY,
            errors=errors,
        )


# -----------------------------------------------------------------------------
# Exception Handlers
# -----------------------------------------------------------------------------

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom application exceptions.
    
    Converts AppException to standard error response.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            message=exc.message,
            status_code=exc.status_code,
            errors=exc.errors if exc.errors else None,
        ),
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError],
) -> JSONResponse:
    """
    Handle Pydantic validation errors.
    
    Converts validation errors to standard error response format.
    """
    errors = []
    
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "code": error["type"],
        })
    
    return JSONResponse(
        status_code=StatusCode.UNPROCESSABLE_ENTITY,
        content=error_response(
            message=ResponseMessage.VALIDATION_ERROR,
            status_code=StatusCode.UNPROCESSABLE_ENTITY,
            errors=errors,
        ),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions.
    
    Catches any exception not handled by other handlers.
    Logs the error and returns a generic error response.
    """
    import logging
    
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=StatusCode.INTERNAL_SERVER_ERROR,
        content=error_response(
            message=ResponseMessage.INTERNAL_ERROR,
            status_code=StatusCode.INTERNAL_SERVER_ERROR,
        ),
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle FastAPI HTTP exceptions.
    
    Converts HTTPException to standard error response.
    """
    from fastapi.exceptions import HTTPException
    
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                message=exc.detail,
                status_code=exc.status_code,
            ),
        )
    
    # Fallback to generic handler
    return await generic_exception_handler(request, exc)


# -----------------------------------------------------------------------------
# Exception Handler Registration
# -----------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI app.
    
    Call this during application initialization.
    
    Args:
        app: FastAPI application instance
    """
    from fastapi.exceptions import HTTPException
    
    # Custom application exceptions
    app.add_exception_handler(AppException, app_exception_handler)
    
    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # HTTP exceptions
    app.add_exception_handler(HTTPException, http_exception_handler)
    
    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
