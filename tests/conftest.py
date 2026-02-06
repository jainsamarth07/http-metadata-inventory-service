"""
Shared pytest fixtures for the test suite.

Uses mongomock-motor for an in-memory MongoDB so tests run without
a real database, and asgi-lifespan to drive the FastAPI lifespan.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import mongodb as mongodb_module
from app.services import collector as collector_module
from app.main import app


@pytest_asyncio.fixture()
async def mock_db():
    """
    Provide a mongomock-motor database and patch the module-level
    reference so the rest of the application uses it transparently.
    """
    from mongomock_motor import AsyncMongoMockClient

    client = AsyncMongoMockClient()
    db = client["test_metadata_inventory"]

    # Create the same index the real startup would create
    await db.metadata.create_index("url", unique=True)

    with patch.object(mongodb_module, "_client", client), \
         patch.object(mongodb_module, "_database", db):
        yield db

    # Clean up
    client.close()


@pytest_asyncio.fixture(autouse=True)
async def mock_http_client():
    """
    Provide a mock shared HTTP client so collector tests
    don't require a real initialised client.
    """
    mock_client = AsyncMock(spec=AsyncClient)
    with patch.object(collector_module, "_http_client", mock_client):
        yield mock_client


@pytest_asyncio.fixture()
async def async_client(mock_db) -> AsyncClient:
    """
    Async HTTP test client wired to the FastAPI app.
    Lifespan is NOT triggered (we already patched the DB above).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
