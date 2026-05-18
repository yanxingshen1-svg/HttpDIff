"""HTTP request execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx


class RequestError(Exception):
    """Raised when an HTTP request fails."""


@dataclass
class RequestConfig:
    """Configuration for an HTTP request."""

    url: str
    method: str = "GET"
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    timeout: float = 30.0


@dataclass
class Response:
    """A simplified HTTP response with the parsed JSON body."""

    status_code: int
    headers: dict[str, str]
    data: Any
    elapsed: float


def execute(config: RequestConfig) -> Response:
    """Execute a single HTTP request and return the parsed JSON response.

    Raises ``RequestError`` on network failures, timeouts, or non-JSON
    responses.  Non-2xx status codes are *not* treated as errors — the
    caller (``diff``) decides what to compare.
    """
    try:
        with httpx.Client(timeout=config.timeout, follow_redirects=True) as client:
            resp = client.request(
                method=config.method,
                url=config.url,
                headers=config.headers or None,
                json=config.body if config.method in ("POST", "PUT", "PATCH") else None,
            )
    except httpx.TimeoutException:
        raise RequestError(f"Request timed out after {config.timeout}s: {config.url}")
    except httpx.RequestError as e:
        raise RequestError(f"Request failed: {e}")

    try:
        data = resp.json()
    except (ValueError, httpx.DecodingError):
        raise RequestError(
            f"Response is not valid JSON (status={resp.status_code}, "
            f"content-type={resp.headers.get('content-type', 'N/A')}): {config.url}"
        )

    return Response(
        status_code=resp.status_code,
        headers=dict(resp.headers),
        data=data,
        elapsed=resp.elapsed.total_seconds(),
    )
