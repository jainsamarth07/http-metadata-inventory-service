"""
HTTP metadata collector.

Responsible for fetching headers, cookies, and page source
from a given URL using httpx (async HTTP client).

A shared AsyncClient is used for connection pooling and efficient
resource management across multiple requests.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Shared HTTP client — initialised/closed via app lifespan
_http_client: httpx.AsyncClient | None = None


def create_http_client() -> None:
    """Create the shared httpx client (called at app startup)."""
    global _http_client
    _http_client = httpx.AsyncClient(
        timeout=settings.request_timeout,
        follow_redirects=True,
        limits=httpx.Limits(max_connections=50, max_keepalive_connections=10),
    )
    logger.info("Shared HTTP client created.")


async def close_http_client() -> None:
    """Close the shared httpx client (called at app shutdown)."""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("Shared HTTP client closed.")


def _get_client() -> httpx.AsyncClient:
    """Return the shared HTTP client, raising if not initialised."""
    if _http_client is None:
        raise RuntimeError("HTTP client is not initialised. Call create_http_client() first.")
    return _http_client


async def collect_metadata(url: str) -> dict:
    """
    Fetch HTTP metadata (headers, cookies, page source) for a given URL.

    Uses the shared httpx.AsyncClient for connection pooling, avoiding
    the overhead of creating a new TCP connection for every request.

    Args:
        url: The fully-qualified URL to collect metadata from.

    Returns:
        A dictionary containing 'headers', 'cookies', and 'page_source'.

    Raises:
        httpx.HTTPStatusError: If the response indicates an HTTP error.
        httpx.RequestError: If a network / connection error occurs.
    """
    logger.info("Collecting metadata for URL: %s", url)

    client = _get_client()
    response = await client.get(url)
    response.raise_for_status()

    headers = dict(response.headers)
    cookies = dict(response.cookies)
    page_source = response.text

    logger.info(
        "Metadata collected for %s — headers: %d, cookies: %d, page_source length: %d",
        url,
        len(headers),
        len(cookies),
        len(page_source),
    )

    return {
        "headers": headers,
        "cookies": cookies,
        "page_source": page_source,
    }
