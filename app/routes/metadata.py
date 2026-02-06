"""
API route definitions for the HTTP Metadata Inventory Service.

Endpoints:
    POST /metadata  — collect and store metadata for a URL
    GET  /metadata  — retrieve stored metadata (or trigger background collection)
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import JSONResponse

from app.models.metadata import (
    AcceptedResponse,
    CreatedResponse,
    ErrorResponse,
    MetadataResponse,
    URLRequest,
)
from app.services.metadata_service import (
    create_metadata_record,
    get_metadata_record,
    schedule_background_collection,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metadata", tags=["Metadata"])


# ---------------------------------------------------------------------------
# POST /metadata
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=CreatedResponse,
    status_code=201,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL supplied."},
        502: {"model": ErrorResponse, "description": "Failed to reach the target URL."},
    },
    summary="Collect metadata for a URL",
    description=(
        "Accepts a URL, fetches its HTTP headers, cookies, and page source, "
        "then stores the result in MongoDB."
    ),
)
async def post_metadata(body: URLRequest) -> CreatedResponse:
    """Create a metadata record for the given URL."""
    url = str(body.url)

    try:
        await create_metadata_record(url)
    except httpx.HTTPStatusError as exc:
        logger.error("HTTP error collecting %s: %s", url, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Target URL returned HTTP {exc.response.status_code}.",
        )
    except httpx.RequestError as exc:
        logger.error("Network error collecting %s: %s", url, exc)
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach the target URL: {exc}",
        )

    return CreatedResponse(url=url)


# ---------------------------------------------------------------------------
# GET /metadata
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=MetadataResponse,
    responses={
        202: {"model": AcceptedResponse, "description": "Metadata is being collected."},
        400: {"model": ErrorResponse, "description": "Invalid URL supplied."},
    },
    summary="Retrieve metadata for a URL",
    description=(
        "Looks up metadata for the given URL. If found, returns the full "
        "dataset. If not found, returns 202 Accepted and triggers background "
        "collection so the data will be available on subsequent requests."
    ),
)
async def get_metadata(
    url: str = Query(
        ...,
        description="The fully-qualified URL to look up.",
        examples=["https://example.com"],
    ),
) -> MetadataResponse | JSONResponse:
    """Retrieve metadata for the requested URL."""
    # Basic URL validation
    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="URL must start with http:// or https://")

    record = await get_metadata_record(url)

    if record is not None:
        # Cache hit — return the full dataset
        return MetadataResponse(**record.model_dump())

    # Cache miss — schedule background collection and respond immediately
    schedule_background_collection(url)

    return JSONResponse(
        status_code=202,
        content=AcceptedResponse(url=url).model_dump(),
    )
