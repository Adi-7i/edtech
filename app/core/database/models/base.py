"""
Base model utilities for MongoDB + Pydantic integration.

Provides:
- PyObjectId: Custom type for MongoDB ObjectId handling in Pydantic v2
- MongoBaseModel: Base class with common fields (id, timestamps)
- Common field types and validators
"""

from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field
from pydantic_core import core_schema


# -----------------------------------------------------------------------------
# Custom ObjectId Type for Pydantic v2
# -----------------------------------------------------------------------------

class _ObjectIdPydanticAnnotation:
    """
    Pydantic v2 compatible ObjectId type.
    Handles validation, serialization, and JSON schema generation.
    """
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: Any,
    ) -> core_schema.CoreSchema:
        """Define how Pydantic should validate and serialize ObjectId."""
        
        def validate_object_id(value: Any) -> ObjectId:
            """Validate and convert to ObjectId."""
            if isinstance(value, ObjectId):
                return value
            if isinstance(value, str):
                if ObjectId.is_valid(value):
                    return ObjectId(value)
                raise ValueError(f"Invalid ObjectId string: {value}")
            raise ValueError(f"Invalid ObjectId type: {type(value)}")
        
        def serialize_object_id(value: ObjectId) -> str:
            """Serialize ObjectId to string."""
            return str(value)
        
        return core_schema.no_info_plain_validator_function(
            validate_object_id,
            serialization=core_schema.plain_serializer_function_ser_schema(
                serialize_object_id,
                info_arg=False,
                return_schema=core_schema.str_schema(),
            ),
        )
    
    @classmethod
    def __get_pydantic_json_schema__(cls, _core_schema: Any, handler: Any) -> dict:
        """Define JSON schema for ObjectId (as string)."""
        return {"type": "string", "pattern": "^[a-fA-F0-9]{24}$"}


# Annotated type for use in Pydantic models
PyObjectId = Annotated[ObjectId, _ObjectIdPydanticAnnotation]


# -----------------------------------------------------------------------------
# Base Model with Common Fields
# -----------------------------------------------------------------------------

class MongoBaseModel(BaseModel):
    """
    Base model for all MongoDB documents.
    
    Provides:
    - id: MongoDB _id field mapped to 'id'
    - created_at: Document creation timestamp (UTC)
    - updated_at: Last modification timestamp (UTC)
    
    Configuration:
    - Allows arbitrary types (for ObjectId)
    - Populates by field name
    - Serializes ObjectId to string in JSON
    """
    
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
        str_strip_whitespace=True,
    )
    
    # MongoDB _id field, aliased as 'id' for API responses
    id: Optional[PyObjectId] = Field(
        default=None,
        alias="_id",
        description="MongoDB document ID"
    )
    
    # Automatic timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Document creation timestamp (UTC)"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last modification timestamp (UTC)"
    )
    
    def model_dump_mongo(self, **kwargs) -> dict:
        """
        Serialize model for MongoDB insertion.
        Excludes None values and unset fields by default.
        """
        data = self.model_dump(by_alias=True, exclude_none=True, **kwargs)
        return data
    
    @classmethod
    def from_mongo(cls, data: dict):
        """
        Create model instance from MongoDB document.
        Handles _id to id mapping automatically.
        """
        if data is None:
            return None
        return cls(**data)


# -----------------------------------------------------------------------------
# Common Field Types
# -----------------------------------------------------------------------------

class TimestampMixin(BaseModel):
    """Mixin for models that only need timestamps without id."""
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Record creation timestamp (UTC)"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last modification timestamp (UTC)"
    )


class SoftDeleteMixin(BaseModel):
    """Mixin for models with soft delete capability."""
    
    is_deleted: bool = Field(
        default=False,
        description="Soft delete flag"
    )
    deleted_at: Optional[datetime] = Field(
        default=None,
        description="Deletion timestamp (UTC)"
    )


# -----------------------------------------------------------------------------
# Common Validators
# -----------------------------------------------------------------------------

def validate_non_empty_string(value: str) -> str:
    """Ensure string is not empty after stripping whitespace."""
    if not value or not value.strip():
        raise ValueError("Field cannot be empty")
    return value.strip()


def validate_positive_int(value: int) -> int:
    """Ensure integer is positive."""
    if value < 0:
        raise ValueError("Value must be positive")
    return value


def validate_percentage(value: float) -> float:
    """Ensure value is between 0 and 100."""
    if not 0 <= value <= 100:
        raise ValueError("Percentage must be between 0 and 100")
    return value
