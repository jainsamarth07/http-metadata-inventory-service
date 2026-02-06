"""
MongoDB connection management and database operations.

Uses Motor (async MongoDB driver) for non-blocking database access.
Implements connection retry logic for resilience during startup.
"""

import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level references managed via lifespan
_client: AsyncIOMotorClient | None = None
_database: AsyncIOMotorDatabase | None = None

# Retry configuration for startup resilience
_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 2  # seconds (exponential backoff: 2, 4, 8, 16, 32)


async def connect_to_mongodb() -> None:
    """
    Establish a connection to MongoDB with retry logic.

    Retries up to ``_MAX_RETRIES`` times with exponential backoff so the
    application remains stable during database startup delays.
    Creates indexes for optimised lookups on the 'url' field.
    """
    global _client, _database

    logger.info("Connecting to MongoDB at %s ...", settings.mongodb_url)

    _client = AsyncIOMotorClient(
        settings.mongodb_url,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )

    _database = _client[settings.mongodb_db_name]

    # Retry loop — handles database startup delays gracefully
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            await _client.admin.command("ping")
            logger.info("Successfully connected to MongoDB (attempt %d).", attempt)
            break
        except Exception as exc:
            if attempt == _MAX_RETRIES:
                logger.error("Failed to connect to MongoDB after %d attempts.", _MAX_RETRIES)
                raise
            delay = _RETRY_BASE_DELAY ** attempt
            logger.warning(
                "MongoDB not ready (attempt %d/%d): %s — retrying in %ds …",
                attempt,
                _MAX_RETRIES,
                exc,
                delay,
            )
            await asyncio.sleep(delay)

    # Create a unique index on 'url' for fast lookups and deduplication
    await _database.metadata.create_index("url", unique=True)
    logger.info("Database indexes ensured.")


async def close_mongodb_connection() -> None:
    """Gracefully close the MongoDB connection."""
    global _client, _database

    if _client is not None:
        _client.close()
        _client = None
        _database = None
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """
    Return the active database instance.

    Raises:
        RuntimeError: If the database connection has not been initialised.
    """
    if _database is None:
        raise RuntimeError("Database is not initialised. Call connect_to_mongodb() first.")
    return _database
