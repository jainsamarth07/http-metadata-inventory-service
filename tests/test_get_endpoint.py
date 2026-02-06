"""
Tests for GET /api/v1/metadata endpoint.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_get_metadata_cache_hit(async_client, mock_db):
    """GET should return 200 with full metadata when the record exists."""
    # Seed the database with a record
    now = datetime.now(timezone.utc)
    await mock_db.metadata.insert_one({
        "url": "https://example.com",
        "headers": {"server": "nginx"},
        "cookies": {"token": "xyz"},
        "page_source": "<html>cached</html>",
        "created_at": now,
        "updated_at": now,
    })

    response = await async_client.get(
        "/api/v1/metadata",
        params={"url": "https://example.com"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["url"] == "https://example.com"
    assert data["headers"]["server"] == "nginx"
    assert data["cookies"]["token"] == "xyz"
    assert data["page_source"] == "<html>cached</html>"


@pytest.mark.asyncio
async def test_get_metadata_cache_miss(async_client):
    """GET should return 202 and schedule background collection on cache miss."""
    with patch(
        "app.routes.metadata.schedule_background_collection",
        return_value=True,
    ) as mock_schedule:
        response = await async_client.get(
            "/api/v1/metadata",
            params={"url": "https://unknown.example.com"},
        )

    assert response.status_code == 202
    data = response.json()
    assert "accepted" in data["message"].lower() or "background" in data["message"].lower()
    assert data["url"] == "https://unknown.example.com"
    mock_schedule.assert_called_once_with("https://unknown.example.com")


@pytest.mark.asyncio
async def test_get_metadata_invalid_url(async_client):
    """GET with a non-HTTP URL should return 400."""
    response = await async_client.get(
        "/api/v1/metadata",
        params={"url": "ftp://invalid-protocol.com"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_metadata_missing_param(async_client):
    """GET without the required 'url' param should return 422."""
    response = await async_client.get("/api/v1/metadata")
    assert response.status_code == 422
