"""
Tests for /auth/register, /auth/login, /auth/refresh, /auth/me.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(async_client: AsyncClient, register_payload: dict):
    response = await async_client.post("/auth/register", json=register_payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == register_payload["email"]
    assert body["full_name"] == register_payload["full_name"]
    # default role per auth_service.register()
    assert body["role"] == "operator"
    assert body["is_active"] is True
    assert "id" in body
    # never leak the hash in the response
    assert "hashed_password" not in body


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_409(
    async_client: AsyncClient, register_payload: dict
):
    first = await async_client.post("/auth/register", json=register_payload)
    assert first.status_code == 201, first.text

    second = await async_client.post("/auth/register", json=register_payload)
    assert second.status_code == 409
    assert "already registered" in second.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_password_too_short_returns_422(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={"email": "short@example.com",
              "password": "abc123", "full_name": "X"},
    )
    assert response.status_code == 422  # Pydantic min_length=8 validation


@pytest.mark.asyncio
async def test_register_invalid_email_returns_422(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "SecurePass123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient, registered_user: dict):
    response = await async_client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(
    async_client: AsyncClient, registered_user: dict
):
    response = await async_client.post(
        "/auth/login",
        json={"email": registered_user["email"],
              "password": "WrongPassword999"},
    )

    assert response.status_code == 401
    # Generic message to prevent email/account enumeration.
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user_returns_401(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "SecurePass123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_updates_last_login(
    async_client: AsyncClient, auth_headers: dict
):
    # Confirm the logged-in user is active and exists via /me.
    response = await async_client.get("/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["is_active"] is True


@pytest.mark.asyncio
async def test_me_with_valid_token(
    async_client: AsyncClient, auth_headers: dict, registered_user: dict
):
    response = await async_client.get("/auth/me", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == registered_user["email"]
    assert body["role"] == "operator"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(async_client: AsyncClient):
    response = await async_client.get("/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_garbage_token_returns_401(async_client: AsyncClient):
    response = await async_client.get(
        "/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_returns_new_access_token(
    async_client: AsyncClient, registered_user: dict
):
    login = await async_client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    refresh_token = login.json()["refresh_token"]

    response = await async_client.post(
        "/auth/refresh", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_with_invalid_token_returns_401(async_client: AsyncClient):
    response = await async_client.post(
        "/auth/refresh", json={"refresh_token": "garbage-not-a-jwt"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_with_access_token_returns_401(
    async_client: AsyncClient, registered_user: dict
):
    """
    Refresh only accepts refresh tokens; 
    access tokens must be rejected.
    """
    login = await async_client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    access_token = login.json()["access_token"]

    response = await async_client.post(
        "/auth/refresh", json={"refresh_token": access_token}
    )
    assert response.status_code == 401
