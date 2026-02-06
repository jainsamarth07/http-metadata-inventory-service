"""
Metadata repository — data-access layer.

Encapsulates all direct MongoDB operations for the metadata collection.
This abstraction makes it straightforward to swap the storage backend
(e.g., PostgreSQL, Redis) without touching business logic or routes.
"""

import logging
from datetime import datetime

from app.database.mongodb import get_database
from app.models.metadata import MetadataDocument

logger = logging.getLogger(__name__)


async def upsert_metadata(doc: MetadataDocument, now: datetime) -> None:
    """
    Insert or update a metadata document in MongoDB.

    On insert, ``created_at`` is set to *now*. On subsequent updates
    only the remaining fields are overwritten.

    Args:
        doc: The metadata document to persist.
        now: The current UTC timestamp.
    """
    db = get_database()

    update_data = doc.to_mongo_dict()
    update_data.pop("created_at", None)

    await db.metadata.update_one(
        {"url": doc.url},
        {
            "$set": update_data,
            "$setOnInsert": {"created_at": now},
        },
        upsert=True,
    )

    logger.info("Metadata record upserted for %s", doc.url)


async def find_metadata_by_url(url: str) -> MetadataDocument | None:
    """
    Look up a metadata document by URL.

    Args:
        url: The fully-qualified URL to search for.

    Returns:
        A MetadataDocument if found, otherwise None.
    """
    db = get_database()
    doc = await db.metadata.find_one({"url": url}, {"_id": 0})

    if doc is None:
        return None

    return MetadataDocument(**doc)
