from __future__ import annotations

import os
from celery import Celery
from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import Session

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.models import (
    DetectionEvent,
    EventType,
    VideoJob,
    VideoStatus,
)
from ai_surveillance_system.ml.inference import run_batch_inference
from ai_surveillance_system.ml.model_loader import model_loader
from ai_surveillance_system.ml.postprocessing import (
    ProcessedDetection,
    aggregate_clip_results,
    postprocess,
)
from ai_surveillance_system.ml.preprocessing import extract_clips

settings = get_settings()
logger = get_logger(__name__)

# Celery app
celery_app = Celery(
    "ai_surveillance",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # Prevent a single stuck video from blocking the queue indefinitely
    task_soft_time_limit=600,
    task_time_limit=660,
)

# Synchronous SQLAlchemy engine (Celery workers are sync)


def _get_sync_engine():
    """
    Convert the async DATABASE_URL (asyncpg) to a sync one (psycopy2)
    for use inside Celery tasks.
    """
    url = settings.DATABASE_URL.replace(
        "postgresql+asyncpg://",
        "postgresql+psycopg2://"
    )
    return create_engine(url, pool_pre_ping=True)


# Label -> DB EventType Mapping
_EVENT_TYPE_MAP: dict[str, EventType] = {
    "violence": EventType.VIOLENCE,
    "nonviolence": EventType.NORMAL  # non-threat clips are not persisted

    # Extend here when model gains fire/intrusion classes:
    # "fire": EventType.FIRE,
    # "intrusion": EventType.INTRUSION
}

# Internal Helpers


def _update_job_status(
        session: Session,
        job_id: str,
        status: VideoStatus,
        error_message: str | None = None,
) -> None:
    """
    Update a video job's status in the database
    and commit the change.
    """
    session.execute(
        update(VideoJob)
        .where(VideoJob.id == job_id)
        .values(status=status, error_message=error_message)
    )
    session.commit()


def _get_job(session: Session, job_id: str) -> VideoJob | None:
    """
    Fetch a VideoJob by ID,
    returning the job if found or None otherwise.
    """
    return session.execute(
        select(VideoJob).where(VideoJob.id == job_id)
    ).scalar_one_or_none()


def _persist_detection(
        session: Session,
        job_id: str,
        detection: ProcessedDetection,
) -> None:
    """
    Persist one confirmed-threat ProcessedDetection as a DetectionEvent row.
    """
    event_type = _EVENT_TYPE_MAP.get(detection.label, EventType.UNKNOWN)

    db_event = DetectionEvent(
        job_id=job_id,
        event_type=event_type,
        confidence=detection.confidence,
        frame_path=detection.frame_paths[0] if detection.frame_paths else None,
        frame_number=detection.frame_number,
        source="upload"
    )

    session.add(db_event)
    session.commit()

    if len(detection.frame_paths) > 1:
        logger.info(f" Detection persisted (job={job_id}) | "
                    f" evidence frames: {detection.frame_paths}"
                    )

# Processing pipeline


def _process_video(job: VideoJob, session: Session) -> int:
    """
    Run the full ML pipeline on one video.
    Returns the number of threat events persisted.
    """
    video_path = job.stored_path

    # Extract sliding-window clips from the video
    BATCH_SIZE = 8   # clips per GPU batch

    all_detections: list[ProcessedDetection] = []

    clip_buffer: list = []
    idx_buffer: list[list[int]] = []

    for clip_tensor, frame_indices in extract_clips(video_path, overlap=0.5):
        clip_buffer.append(clip_tensor)
        idx_buffer.append(frame_indices)

        if len(clip_buffer) == BATCH_SIZE:
            detections = _run_and_postprocess_batch(
                clip_buffer, idx_buffer, job.id
            )
            all_detections.extend(detections)
            clip_buffer.clear()
            idx_buffer.clear()

    # Flush remaining clips
    if clip_buffer:
        detections = _run_and_postprocess_batch(
            clip_buffer, idx_buffer, job.id
        )
        all_detections.extend(detections)

    if not all_detections:
        logger.warning(f"No clips extracted from video: {video_path}")
        return 0

    # Aggregate clips → single per-video verdict
    verdict = aggregate_clip_results(all_detections, min_threat_clips=1)
    _persist_detection(session, job.id, verdict)

    if verdict.is_threat:
        logger.info(
            f"Job {job.id} → THREAT | "
            f"label={verdict.label} confidence={verdict.confidence:.3f}"
        )
        return 1

    logger.info(f"Job {job.id} → CLEAR after {len(all_detections)} clips")
    return 0


def _run_and_postprocess_batch(
    clip_buffer: list,
    idx_buffer: list[list[int]],
    job_id: str,
) -> list[ProcessedDetection]:
    """
    Run batch inference on a list of clip tensors then postprocess each.
    Returns a list of ProcessedDetection (including non-threats).
    """
    inference_results = run_batch_inference(
        clip_buffer,
        frame_indices_list=idx_buffer,
    )

    detections: list[ProcessedDetection] = []
    for result in inference_results:
        processed = postprocess(
            inference_result=result,
            raw_frames=None,   # BGR frames not retained in batch mode
            frame_number=result.frame_indices[0] if result.frame_indices else None,
            job_id=job_id,
            confidence_threshold=settings.CONFIDENCE_THRESHOLD,
        )
        detections.append(processed)

    return detections

# Celery task


@celery_app.task(
    bind=True,
    name="workers.process_video_task",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def process_video_task(self, job_id: str) -> dict:
    """
    Entry point called by the upload route after a video is saved.
    """
    logger.info(f"process_video_task started | job_id={job_id}")

    # Ensure model is loaded in the worker process
    try:
        model_loader.load()
    except Exception as exc:
        logger.error(f"Model load failed in worker: {exc}")
        raise self.retry(exc=exc)

    engine = _get_sync_engine()

    with Session(engine) as session:
        job = _get_job(session, job_id)
        if job is None:
            if self.request.retries >= 3:
                logger.error(
                    f"Job {job_id} never became visible after retries — giving up")
                return {"job_id": job_id, "status": "not_found", "threat_events_found": 0}
            logger.warning(
                f"Job {job_id} not yet visible to worker — retrying")
            raise self.retry(countdown=1)

        if job.status not in (VideoStatus.QUEUED, VideoStatus.FAILED):
            logger.warning(
                f"Job {job_id} has status={job.status} — skipping re-processing."
            )
            return {"job_id": job_id, "status": job.status, "threat_events_found": 0}

        # Mark as processing
        _update_job_status(session, job_id, VideoStatus.PROCESSING)

        try:
            threat_count = _process_video(job, session)
            _update_job_status(session, job_id, VideoStatus.COMPLETED)
            logger.info(
                f"process_video_task complete | job_id={job_id} | "
                f"threats={threat_count}"
            )
            return {
                "job_id": job_id,
                "status": "completed",
                "threat_events_found": threat_count,
            }

        except Exception as exc:
            error_msg = str(exc)
            logger.error(
                f"process_video_task failed | job_id={job_id} | error={error_msg}",
                exc_info=True,
            )
            _update_job_status(session, job_id, VideoStatus.FAILED, error_msg)
            raise self.retry(exc=exc)
