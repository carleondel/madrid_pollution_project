"""HTTP client helpers with bounded retries."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DEFAULT_TIMEOUT_SECONDS = 120.0


@contextmanager
def managed_client() -> Iterator[httpx.Client]:
    """Yield the shared synchronous HTTP client used by ingestion commands."""

    with httpx.Client(
        follow_redirects=True,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        headers={"User-Agent": "madrid-pollution/0.1 (+public-data-research)"},
    ) as client:
        yield client


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def get_bytes(client: httpx.Client, url: str, params: dict[str, object] | None = None) -> bytes:
    """Download a resource and raise for transport or HTTP failures."""

    response = client.get(url, params=params)
    response.raise_for_status()
    return response.content


@retry(
    retry=retry_if_exception_type((httpx.TransportError, httpx.HTTPStatusError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def get_json(
    client: httpx.Client,
    url: str,
    params: dict[str, object] | None = None,
) -> dict[str, object]:
    """Download and validate a JSON object response."""

    response = client.get(url, params=params)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object from {url}")
    return payload
