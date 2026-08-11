from __future__ import annotations

from pathlib import Path
import uuid
from datetime import datetime, timezone
from typing import Optional

import cv2
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.models import DetectionEvent, EventType
from ai_surveillance_system.ml.inference import InferenceResult, run_inference
from ai_surveillance_system.ml.postprocessing import ProcessedDetection, postprocess
from ai_surveillance_system.ml.preprocessing import StreamFrameBuffer
from ai_surveillance_system.schemas.detection import DetectionCreate, DetectionResponse

settings = get_settings()
logger = get_logger(__name__)

# Label → DB EventType
_LABEL_TO_DB_EVENT_TYPE: dict[str, EventType] = {
    "violence": EventType.VIOLENCE,
    "nonviolence":   EventType.NORMAL,
    # Add "fire": EventType.FIRE etc. when model is extended
}


class DetectionService:
    """
    Orchestrates the ML pipeline and persists detection results.
    """
    # Write methods

    async def record_detection(
        self,
        data: DetectionCreate,
        db:   AsyncSession,
    ) -> DetectionEvent:
        """
        Persist a detection event returned by the ML pipeline.
        Called directly by celery_worker after processing a video.
        """
        event = DetectionEvent(
            id=str(uuid.uuid4()),
            job_id=data.job_id,
            event_type=data.event_type,
            confidence=data.confidence,
            frame_path=data.frame_path,
            frame_number=data.frame_number,
            source=data.source,
            timestamp=datetime.now(timezone.utc),
        )

        db.add(event)
        await db.flush()
        await db.refresh(event)

        logger.info(
            f"DetectionEvent recorded | "
            f"id={event.id} "
            f"type={event.event_type} "
            f"conf={event.confidence:.2f} "
            f"job={event.job_id}"
        )

        return event

    async def mark_notified(
        self,
        detection_id: str,
        channel: str,
        db: AsyncSession,
    ) -> bool:
        """
        Mark a detection event as notified.
        Returns True if the event was found and updated, False otherwise.
        """
        event = await self.get_detection_by_id(detection_id, db)

        if not event:
            logger.warning(
                f"mark_notified: detection {detection_id!r} not found"
            )
            return False

        event.notified = True
        event.notification_channel = channel
        event.notified_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info(
            f"Detection {detection_id} marked notified via {channel}"
        )
        return True

    # Read methods
    async def get_detections(
        self,
        db: AsyncSession,
        job_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[DetectionEvent]]:
        """
        Return (total_count, page) for the detections list endpoint.
        Filters are applied only when provided.
        """
        query = select(DetectionEvent).order_by(
            DetectionEvent.timestamp.desc())
        count_query = select(func.count()).select_from(DetectionEvent)

        if job_id:
            query = query.where(DetectionEvent.job_id == job_id)
            count_query = count_query.where(DetectionEvent.job_id == job_id)

        if event_type:
            try:
                et = EventType(event_type.lower())
            except ValueError:
                logger.warning(f"Unknown event_type filter: {event_type!r}")
                return 0, []

            query = query.where(DetectionEvent.event_type == et)
            count_query = count_query.where(DetectionEvent.event_type == et)

        total = (await db.execute(count_query)).scalar_one()
        items = (await db.execute(query.limit(limit).offset(offset))).scalars().all()

        return total, list(items)

    async def get_detection_by_id(
        self,
        detection_id: str,
        db:           AsyncSession,
    ) -> DetectionEvent | None:
        """Fetch a single detection event by ID."""
        result = await db.execute(
            select(DetectionEvent).where(DetectionEvent.id == detection_id)
        )
        return result.scalar_one_or_none()

    # Stream path
    async def push_stream_frame(
        self,
        frame_bgr:   np.ndarray,
        buffer:      StreamFrameBuffer,
        db:          AsyncSession,
        job_id:      Optional[str] = None,
        client_host: str = "unknown",
    ) -> Optional[ProcessedDetection]:
        """
        Push one decoded BGR frame into the rolling buffer.
        """
        clip_tensor, frame_indices = buffer.push(frame_bgr)

        if clip_tensor is None:
            return None

        inference_result: InferenceResult = run_inference(
            clip_tensor, frame_indices=frame_indices
        )

        processed = postprocess(
            inference_result=inference_result,
            raw_frames=None,
            frame_number=frame_indices[0] if frame_indices else None,
            job_id=job_id,
            confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        )

        logger.info(
            f"Stream inference | client={client_host} | "
            f"frames={frame_indices[0] if frame_indices else '?'}–"
            f"{frame_indices[-1] if frame_indices else '?'} | "
            f"label={processed.label} "
            f"event_type={processed.event_type} "
            f"confidence={processed.confidence:.3f} "
            f"threat={processed.is_threat}"
        )

        if processed.is_threat:
            await self._persist_stream_detection(db, processed, job_id)

        return processed

    async def push_stream_frame_bytes(
        self,
        frame_bytes: bytes,
        buffer:      StreamFrameBuffer,
        db:          AsyncSession,
        job_id:      Optional[str] = None,
        client_host: str = "unknown",
    ) -> tuple[Optional[ProcessedDetection], Optional[np.ndarray]]:
        """
        Convenience wrapper for WebSocket handlers that receive raw bytes.
        Decodes JPEG/PNG bytes then delegates to push_stream_frame().
        """
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if frame_bgr is None:
            raise ValueError(
                "Failed to decode frame bytes — invalid or corrupt image data."
            )

        processed = await self.push_stream_frame(
            frame_bgr,
            buffer,
            db,
            job_id=job_id,
            client_host=client_host,
        )

        raw = frame_bgr if processed is not None else None
        return processed, raw

    # Threshold helper
    def should_alert(self, confidence: float) -> bool:
        """
        Returns True if confidence exceeds the configured threshold.
        Used by notification_service before sending alerts.
        """
        return confidence >= settings.CONFIDENCE_THRESHOLD

    # Internal helpers
    async def _persist_stream_detection(
        self,
        db:        AsyncSession,
        processed: ProcessedDetection,
        job_id:    Optional[str],
    ) -> DetectionEvent:
        """Write a confirmed stream threat to the DB."""
        event_type = _LABEL_TO_DB_EVENT_TYPE.get(
            processed.label, EventType.UNKNOWN
        )

        db_event = DetectionEvent(
            id=str(uuid.uuid4()),
            job_id=job_id,
            event_type=event_type,
            confidence=processed.confidence,
            frame_path=processed.frame_paths[0] if processed.frame_paths else None,
            frame_number=processed.frame_number,
            timestamp=datetime.now(timezone.utc),
            source="stream",
        )

        db.add(db_event)
        await db.flush()
        await db.refresh(db_event)

        logger.info(
            f"Stream detection persisted | "
            f"id={db_event.id} | "
            f"type={event_type} | "
            f"confidence={processed.confidence:.3f}"
        )
        return db_event

    async def delete_detection(self, detection_id: str, db: AsyncSession) -> bool:
        event = await self.get_detection_by_id(detection_id, db)
        if not event:
            return False
        if event.frame_path:
            # clean up evidence file too
            Path(event.frame_path).unlink(missing_ok=True)
        await db.delete(event)
        await db.flush()
        logger.info(f"Detection {detection_id} deleted")
        return True


# Module-level singleton
detection_service = DetectionService()
