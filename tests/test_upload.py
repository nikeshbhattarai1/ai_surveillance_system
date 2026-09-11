"""
Tests for POST /api/v1/upload.
"""

from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.models import VideoJob, VideoStatus


def _fake_video_file(filename: str = "clip.mp4", content: bytes = b"fake video bytes"):
    return {"file": (filename, io.BytesIO(content), "video/mp4")}


@pytest.mark.asyncio
async def test_upload_without_auth_returns_403(async_client: AsyncClient):
    response = await async_client.post("/api/v1/upload", files=_fake_video_file())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_success(
    async_client: AsyncClient, auth_headers: dict, db_session: AsyncSession
):
    with patch(
        "ai_surveillance_system.api.routes.upload.process_video_task.delay"
    ) as mock_delay:
        response = await async_client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files=_fake_video_file(
                filename="incident.mp4", content=b"x" * 1024),
        )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["filename"] == "incident.mp4"
    assert body["status"] == VideoStatus.QUEUED.value
    assert body["size_kb"] == pytest.approx(1.0, rel=0.05)
    assert "job_id" in body
    assert "uploaded_at" in body
    assert "message" in body

    # Celery task was enqueued with the new job's id
    mock_delay.assert_called_once_with(body["job_id"])

    # A VideoJob row was actually created
    result = await db_session.execute(
        select(VideoJob).where(VideoJob.id == body["job_id"])
    )
    job = result.scalar_one()
    assert job.original_filename == "incident.mp4"
    assert job.status == VideoStatus.QUEUED
    assert job.file_size_bytes == 1024

    # Clean up the file actually written to disk
    stored_path = Path(job.stored_path)
    if stored_path.exists():
        stored_path.unlink()


@pytest.mark.asyncio
async def test_upload_rejects_unsupported_extension(
    async_client: AsyncClient, auth_headers: dict
):
    with patch("ai_surveillance_system.api.routes.upload.process_video_task.delay"):
        response = await async_client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files={"file": ("notes.txt", io.BytesIO(b"hello"), "text/plain")},
        )

    assert response.status_code == 415
    assert "unsupported media type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_empty_file(async_client: AsyncClient, auth_headers: dict):
    with patch("ai_surveillance_system.api.routes.upload.process_video_task.delay"):
        response = await async_client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files=_fake_video_file(content=b""),
        )

    assert response.status_code == 400
    assert "empty file" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(
    async_client: AsyncClient, auth_headers: dict, monkeypatch
):
    # Set the limit to 0MB so a tiny payload triggers the size check.
    from ai_surveillance_system.services import video_service as video_service_module

    monkeypatch.setattr(video_service_module.settings, "MAX_UPLOAD_SIZE_MB", 0)

    with patch("ai_surveillance_system.api.routes.upload.process_video_task.delay"):
        response = await async_client.post(
            "/api/v1/upload",
            headers=auth_headers,
            files=_fake_video_file(content=b"x" * 2048),
        )

    assert response.status_code == 413
    assert "exceeds size limit" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_missing_file_returns_422(
    async_client: AsyncClient, auth_headers: dict
):
    response = await async_client.post("/api/v1/upload", headers=auth_headers)
    assert response.status_code == 422
