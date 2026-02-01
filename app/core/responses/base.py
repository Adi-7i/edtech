"""
Smart Study Planner - Standard API Response Models

Provides consistent response format across all API endpoints.
All responses follow a standard structure for success and error cases.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

from app.shared.constants import ResponseMessage, StatusCode


# -----------------------------------------------------------------------------
# Generic Type for Data
# -----------------------------------------------------------------------------

T = TypeVar("T")


# -----------------------------------------------------------------------------
# Base Response Models
# -----------------------------------------------------------------------------

class BaseResponse(BaseModel):
    """Base response model with common fields."""
    
    success: bool = Field(
        ...,
        description="Indicates if the request was successful"
    )
    message: str = Field(
        ...,
        description="Human-readable message"
    )
    status_code: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP status code"
    )


class SuccessResponse(BaseResponse, Generic[T]):
    """
    Standard success response format.
    
    Example:
        ```json
        {
            "success": true,
            "message": "Operation completed successfully",
            "status_code": 200,
            "data": {...}
        }
        ```
    """
    
    success: bool = Field(default=True)
    data: Optional[T] = Field(
        default=None,
        description="Response payload data"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Operation completed successfully",
                "status_code": 200,
                "data": {"id": "123", "name": "Example"}
            }
        }
    }


class ErrorDetail(BaseModel):
    """Detailed error information."""
    
    field: Optional[str] = Field(
        default=None,
        description="Field that caused the error (for validation errors)"
    )
    message: str = Field(
        ...,
        description="Error message"
    )
    code: Optional[str] = Field(
        default=None,
        description="Error code for programmatic handling"
    )


class ErrorResponse(BaseResponse):
    """
    Standard error response format.
    
    Example:
        ```json
        {
            "success": false,
            "message": "Validation failed",
            "status_code": 422,
            "errors": [
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "code": "INVALID_EMAIL"
                }
            ]
        }
        ```
    """
    
    success: bool = Field(default=False)
    errors: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="List of detailed errors"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "success": False,
                "message": "Validation failed",
                "status_code": 422,
                "errors": [
                    {
                        "field": "email",
                        "message": "Invalid email format",
                        "code": "INVALID_EMAIL"
                    }
                ]
            }
        }
    }


# -----------------------------------------------------------------------------
# Pagination Models
# -----------------------------------------------------------------------------

class PaginationMeta(BaseModel):
    """Pagination metadata."""
    
    page: int = Field(
        ...,
        ge=1,
        description="Current page number"
    )
    page_size: int = Field(
        ...,
        ge=1,
        description="Items per page"
    )
    total_items: int = Field(
        ...,
        ge=0,
        description="Total number of items"
    )
    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of pages"
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page"
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page"
    )


class PaginatedResponse(SuccessResponse[List[T]], Generic[T]):
    """
    Paginated response format.
    
    Example:
        ```json
        {
            "success": true,
            "message": "Users retrieved successfully",
            "status_code": 200,
            "data": [...],
            "pagination": {
                "page": 1,
                "page_size": 20,
                "total_items": 100,
                "total_pages": 5,
                "has_next": true,
                "has_previous": false
            }
        }
        ```
    """
    
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata"
    )


# -----------------------------------------------------------------------------
# Response Helper Functions
# -----------------------------------------------------------------------------

def success_response(
    data: Any = None,
    message: str = ResponseMessage.SUCCESS,
    status_code: int = StatusCode.OK,
) -> Dict[str, Any]:
    """
    Create a success response.
    
    Args:
        data: Response data payload
        message: Success message
        status_code: HTTP status code
    
    Returns:
        Dict: Success response dictionary
    
    Example:
        ```python
        return success_response(
            data={"id": "123", "name": "John"},
            message="User created successfully",
            status_code=201
        )
        ```
    """
    return {
        "success": True,
        "message": message,
        "status_code": status_code,
        "data": data,
    }


def error_response(
    message: str = ResponseMessage.INTERNAL_ERROR,
    status_code: int = StatusCode.INTERNAL_SERVER_ERROR,
    errors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create an error response.
    
    Args:
        message: Error message
        status_code: HTTP status code
        errors: List of detailed errors
    
    Returns:
        Dict: Error response dictionary
    
    Example:
        ```python
        return error_response(
            message="Validation failed",
            status_code=422,
            errors=[{
                "field": "email",
                "message": "Invalid email",
                "code": "INVALID_EMAIL"
            }]
        )
        ```
    """
    return {
        "success": False,
        "message": message,
        "status_code": status_code,
        "errors": errors,
    }


def paginated_response(
    data: List[Any],
    page: int,
    page_size: int,
    total_items: int,
    message: str = ResponseMessage.SUCCESS,
    status_code: int = StatusCode.OK,
) -> Dict[str, Any]:
    """
    Create a paginated response.
    
    Args:
        data: List of items for current page
        page: Current page number
        page_size: Items per page
        total_items: Total number of items
        message: Success message
        status_code: HTTP status code
    
    Returns:
        Dict: Paginated response dictionary
    """
    import math
    
    total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
    
    return {
        "success": True,
        "message": message,
        "status_code": status_code,
        "data": data,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_previous": page > 1,
        },
    }
