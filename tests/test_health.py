"""
Tests for GET /health.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_valid_response_shape(async_client: AsyncClient):
    response = await async_client.get("/health")

    # Without lifespan, dependencies aren't initialized,
    # so 503 is expected.
    assert response.status_code == 503

    body = response.json()
    assert body["status"] == "unhealthy"
    assert "version" in body
    assert "environment" in body
    assert "dependencies" in body

    deps = body["dependencies"]
    assert set(deps.keys()) == {"db", "redis", "model"}
    for value in deps.values():
        assert value == "not_initialized"


@pytest.mark.asyncio
async def test_health_does_not_require_auth(async_client: AsyncClient):
    # /health must be reachable with no Authorization header at all.
    response = await async_client.get("/health")
    assert response.status_code in (200, 503)
    assert "detail" not in response.json()  # not an auth rejection