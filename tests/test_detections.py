
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.models import DetectionEvent, EventType, VideoJob


async def _create_video_job(db_session: AsyncSession) -> VideoJob:
    job = VideoJob(
        id=str(uuid.uuid4()),
        original_filename="test.mp4",
        stored_path="/tmp/test.mp4",
        file_size_bytes=1024,
    )
    db_session.add(job)
    await db_session.flush()
    await db_session.refresh(job)
    return job


async def _create_detection(
    db_session: AsyncSession,
    *,
    event_type: EventType = EventType.VIOLENCE,
    confidence: float = 0.91,
    job_id: str | None = None,
    source: str = "upload",
) -> DetectionEvent:
    event = DetectionEvent(
        id=str(uuid.uuid4()),
        job_id=job_id,
        event_type=event_type,
        confidence=confidence,
        frame_path=None,
        frame_number=10,
        timestamp=datetime.now(timezone.utc),
        source=source,
    )
    db_session.add(event)
    await db_session.flush()
    await db_session.refresh(event)
    return event


@pytest.mark.asyncio
async def test_list_detections_without_auth_returns_401(async_client: AsyncClient):
    response = await async_client.get("/api/v1/detections")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_detections_empty(async_client: AsyncClient, auth_headers: dict):
    response = await async_client.get("/api/v1/detections", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []
    assert body["limit"] == 50
    assert body["offset"] == 0


@pytest.mark.asyncio
async def test_list_detections_returns_created_event(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    event = await _create_detection(db_session, event_type=EventType.VIOLENCE, confidence=0.87)

    response = await async_client.get("/api/v1/detections", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["id"] == event.id
    assert item["event_type"] == "violence"
    assert item["confidence"] == pytest.approx(0.87)


@pytest.mark.asyncio
async def test_list_detections_filters_by_event_type(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await _create_detection(db_session, event_type=EventType.VIOLENCE)
    await _create_detection(db_session, event_type=EventType.NORMAL)

    response = await async_client.get(
        "/api/v1/detections", params={"event_type": "violence"}, headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["event_type"] == "violence"


@pytest.mark.asyncio
async def test_list_detections_filters_by_job_id(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    target_job = await _create_video_job(db_session)
    other_job = await _create_video_job(db_session)

    await _create_detection(db_session, job_id=target_job.id)
    await _create_detection(db_session, job_id=other_job.id)

    response = await async_client.get(
        "/api/v1/detections", params={"job_id": target_job.id}, headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["job_id"] == target_job.id


@pytest.mark.asyncio
async def test_list_detections_unknown_event_type_returns_empty(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    await _create_detection(db_session, event_type=EventType.VIOLENCE)

    response = await async_client.get(
        "/api/v1/detections",
        params={"event_type": "not-a-real-type"},
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 0
    assert body["items"] == []


@pytest.mark.asyncio
async def test_list_detections_respects_limit_and_offset(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    for _ in range(3):
        await _create_detection(db_session)

    response = await async_client.get(
        "/api/v1/detections", params={"limit": 1, "offset": 1}, headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 1
    assert body["limit"] == 1
    assert body["offset"] == 1


@pytest.mark.asyncio
async def test_get_detection_by_id_success(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    event = await _create_detection(db_session, event_type=EventType.FIRE, confidence=0.77)

    response = await async_client.get(
        f"/api/v1/detections/{event.id}", headers=auth_headers
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == event.id
    assert body["event_type"] == "fire"
    assert body["confidence"] == pytest.approx(0.77)


@pytest.mark.asyncio
async def test_get_detection_by_id_not_found(async_client: AsyncClient, auth_headers: dict):
    missing_id = str(uuid.uuid4())

    response = await async_client.get(
        f"/api/v1/detections/{missing_id}", headers=auth_headers
    )

    assert response.status_code == 404
    assert missing_id in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_detection_without_auth_returns_401(async_client: AsyncClient):
    response = await async_client.get(f"/api/v1/detections/{uuid.uuid4()}")
    assert response.status_code == 401
