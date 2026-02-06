"""
Metadata business-logic service.

Encapsulates all database interactions and orchestrates the
background collection workflow, keeping the route layer thin.

Database access is delegated to the repository layer, ensuring a
clean separation between business logic and data persistence.
"""

import asyncio
import logging
from datetime import datetime, timezone

from app.database.repository import find_metadata_by_url, upsert_metadata
from app.models.metadata import MetadataDocument
from app.services.collector import collect_metadata

logger = logging.getLogger(__name__)

# In-flight tracker — prevents duplicate background tasks for the same URL
_pending_urls: set[str] = set()


async def create_metadata_record(url: str) -> MetadataDocument:
    """
    Collect metadata for *url* and persist it to MongoDB (POST flow).

    If a record for this URL already exists it will be updated with
    fresh data; otherwise a new document is inserted.

    Args:
        url: The fully-qualified URL to process.

    Returns:
        The persisted MetadataDocument.
    """
    raw = await collect_metadata(url)

    now = datetime.now(timezone.utc)

    doc = MetadataDocument(
        url=url,
        headers=raw["headers"],
        cookies=raw["cookies"],
        page_source=raw["page_source"],
        created_at=now,
        updated_at=now,
    )

    await upsert_metadata(doc, now)
    return doc


async def get_metadata_record(url: str) -> MetadataDocument | None:
    """
    Retrieve the metadata record for *url* from MongoDB.

    Returns:
        A MetadataDocument if found, otherwise None.
    """
    return await find_metadata_by_url(url)


async def _background_collect(url: str) -> None:
    """
    Internal background task that collects and stores metadata.

    This runs independently of the request-response cycle.
    On failure it logs the error and removes the URL from the
    in-flight set so it can be retried on the next request.
    """
    try:
        logger.info("Background collection started for %s", url)
        await create_metadata_record(url)
        logger.info("Background collection completed for %s", url)
    except Exception:
        logger.exception("Background collection failed for %s", url)
    finally:
        _pending_urls.discard(url)


def schedule_background_collection(url: str) -> bool:
    """
    Schedule an async background task to collect metadata for *url*.

    Uses asyncio.create_task for internal orchestration — no
    external HTTP self-calls or polling loops.

    Args:
        url: The URL to collect metadata for.

    Returns:
        True if a new task was scheduled, False if one is already in-flight.
    """
    if url in _pending_urls:
        logger.info("Background collection already in-flight for %s", url)
        return False

    _pending_urls.add(url)
    asyncio.create_task(_background_collect(url))
    logger.info("Background collection task scheduled for %s", url)
    return True
