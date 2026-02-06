"""
Tests for POST /api/v1/metadata endpoint.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest


@pytest.mark.asyncio
async def test_post_metadata_success(async_client):
    """POST should collect metadata and return 201 with success message."""
    mock_metadata = {
        "headers": {"content-type": "text/html"},
        "cookies": {"session": "abc123"},
        "page_source": "<html><body>Hello</body></html>",
    }

    with patch(
        "app.services.metadata_service.collect_metadata",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        response = await async_client.post(
            "/api/v1/metadata",
            json={"url": "https://example.com"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["message"] == "Metadata collected and stored successfully."
    assert data["url"] == "https://example.com/"


@pytest.mark.asyncio
async def test_post_metadata_invalid_url(async_client):
    """POST with an invalid URL should return 422 (validation error)."""
    response = await async_client.post(
        "/api/v1/metadata",
        json={"url": "not-a-valid-url"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_metadata_missing_url(async_client):
    """POST without a 'url' field should return 422."""
    response = await async_client.post(
        "/api/v1/metadata",
        json={},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_post_metadata_network_error(async_client):
    """POST should return 502 if the target URL is unreachable."""
    with patch(
        "app.services.metadata_service.collect_metadata",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("Connection refused"),
    ):
        response = await async_client.post(
            "/api/v1/metadata",
            json={"url": "https://unreachable.example.com"},
        )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_post_metadata_upserts_existing(async_client):
    """POST to the same URL twice should update (upsert) the record."""
    mock_metadata = {
        "headers": {"content-type": "text/html"},
        "cookies": {},
        "page_source": "<html>v1</html>",
    }

    with patch(
        "app.services.metadata_service.collect_metadata",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        resp1 = await async_client.post(
            "/api/v1/metadata",
            json={"url": "https://example.com"},
        )
        assert resp1.status_code == 201

    mock_metadata["page_source"] = "<html>v2</html>"

    with patch(
        "app.services.metadata_service.collect_metadata",
        new_callable=AsyncMock,
        return_value=mock_metadata,
    ):
        resp2 = await async_client.post(
            "/api/v1/metadata",
            json={"url": "https://example.com"},
        )
        assert resp2.status_code == 201
