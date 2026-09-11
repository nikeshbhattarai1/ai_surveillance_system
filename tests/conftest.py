"""
Shared pytest fixtures for the AI Surveillance System backend test suite.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.db.session import Base, get_db
from ai_surveillance_system.main import app

settings = get_settings()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def test_engine():
    """
    One engine for the whole test session. Creates all tables once at the
    start and drops them once at the end.
    """
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    One session per test, bound to a single connection wrapped in an outer
    transaction. The transaction is rolled back after the test, so nothing
    written during a test persists into the next one.
    """
    connection = await test_engine.connect()
    transaction = await connection.begin()

    session_factory = async_sessionmaker(
        bind=connection, expire_on_commit=False, class_=AsyncSession
    )
    session = session_factory()

    try:
        yield session
    finally:
        await session.close()
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Share the per-test transactional session across requests.
    This lets requests like "register then login" see uncommitted writes
    without needing an explicit commit.
    """

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def register_payload() -> dict:
    """A valid /auth/register request body, reused across several tests."""
    return {
        "email": "testuser@example.com",
        "password": "SecurePass123",
        "full_name": "Test User",
    }


@pytest_asyncio.fixture
async def registered_user(async_client: AsyncClient, register_payload: dict) -> dict:
    """Registers a user via the real API and returns the request payload used."""
    response = await async_client.post("/auth/register", json=register_payload)
    assert response.status_code == 201, response.text
    return register_payload


@pytest_asyncio.fixture
async def auth_headers(async_client: AsyncClient, registered_user: dict) -> dict:
    """Registers + logs in a user, returns an Authorization header dict."""
    response = await async_client.post(
        "/auth/login",
        json={
            "email": registered_user["email"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
