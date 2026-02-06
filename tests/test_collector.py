"""
Tests for the HTTP metadata collector service.
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.services import collector as collector_module
from app.services.collector import collect_metadata


@pytest.mark.asyncio
async def test_collect_metadata_success():
    """Collector should return headers, cookies, and page_source."""
    mock_response = AsyncMock()
    mock_response.headers = {"content-type": "text/html", "server": "gunicorn"}
    mock_response.cookies = httpx.Cookies({"sid": "abc"})
    mock_response.text = "<html><body>Test</body></html>"
    mock_response.raise_for_status = lambda: None

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_response

    with patch.object(collector_module, "_http_client", mock_client):
        result = await collect_metadata("https://example.com")

    assert "headers" in result
    assert "cookies" in result
    assert "page_source" in result
    assert result["page_source"] == "<html><body>Test</body></html>"


@pytest.mark.asyncio
async def test_collect_metadata_timeout():
    """Collector should raise on timeout."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ReadTimeout("Timed out")

    with patch.object(collector_module, "_http_client", mock_client):
        with pytest.raises(httpx.ReadTimeout):
            await collect_metadata("https://slow.example.com")


@pytest.mark.asyncio
async def test_collect_metadata_connection_error():
    """Collector should raise on connection failure."""
    mock_client = AsyncMock()
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    with patch.object(collector_module, "_http_client", mock_client):
        with pytest.raises(httpx.ConnectError):
            await collect_metadata("https://down.example.com")
