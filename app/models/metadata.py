"""
Pydantic models for request validation, response serialisation,
and internal data representation of URL metadata records.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class URLRequest(BaseModel):
    """Incoming request body containing a URL to collect metadata for."""

    url: HttpUrl = Field(
        ...,
        description="The fully-qualified URL to collect metadata for.",
        examples=["https://example.com"],
    )


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

class MetadataResponse(BaseModel):
    """Full metadata record returned to the client."""

    url: str = Field(..., description="The URL this metadata belongs to.")
    headers: dict = Field(default_factory=dict, description="HTTP response headers.")
    cookies: dict = Field(default_factory=dict, description="HTTP response cookies.")
    page_source: str = Field(default="", description="HTML page source of the URL.")
    created_at: datetime = Field(..., description="Timestamp when the record was created.")
    updated_at: datetime = Field(..., description="Timestamp when the record was last updated.")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "url": "https://example.com",
                    "headers": {"Content-Type": "text/html; charset=UTF-8"},
                    "cookies": {},
                    "page_source": "<!doctype html>...",
                    "created_at": "2026-02-06T12:00:00Z",
                    "updated_at": "2026-02-06T12:00:00Z",
                }
            ]
        }
    }


class AcceptedResponse(BaseModel):
    """Response returned when metadata collection has been queued."""

    message: str = Field(
        default="Request accepted. Metadata is being collected in the background.",
        description="Acknowledgement message.",
    )
    url: str = Field(..., description="The URL that was requested.")


class CreatedResponse(BaseModel):
    """Response returned after a successful POST."""

    message: str = Field(
        default="Metadata collected and stored successfully.",
        description="Success message.",
    )
    url: str = Field(..., description="The URL whose metadata was stored.")


class ErrorResponse(BaseModel):
    """Standard error response body."""

    detail: str = Field(..., description="Human-readable error description.")


# ---------------------------------------------------------------------------
# Internal / DB document model
# ---------------------------------------------------------------------------

class MetadataDocument(BaseModel):
    """Internal representation of a metadata document stored in MongoDB."""

    url: str
    headers: dict = Field(default_factory=dict)
    cookies: dict = Field(default_factory=dict)
    page_source: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_mongo_dict(self) -> dict:
        """Convert the model to a dictionary suitable for MongoDB insertion."""
        data = self.model_dump()
        return data
