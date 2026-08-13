from fastapi import APIRouter, UploadFile, File, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.db.models import VideoStatus, User
from ai_surveillance_system.schemas.video import UploadResponse, VideoJobResponse
from ai_surveillance_system.services.video_service import video_service
from ai_surveillance_system.workers.celery_worker import process_video_task
from ai_surveillance_system.api.deps import get_current_active_user

router = APIRouter(prefix="/api/v1", tags=["Upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a video for analysis",
    description="Streams the file to disk, creates a job record and queues processing.",
)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    job = await video_service.validate_and_save(file, db)

    # enqueue Celery task
    process_video_task.delay(job.id)

    return UploadResponse(
        job_id=job.id,
        filename=job.original_filename,
        size_kb=round(job.file_size_bytes / 1024, 2),
        status=VideoStatus.QUEUED,
        uploaded_at=job.created_at,
        message="Video accepted. Use job_id to track progress.",
    )

@router.get(
    "/jobs/{job_id}",
    response_model=VideoJobResponse,
    summary="Get the processing status of a video job",
)
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    job = await video_service.get_job(job_id, db)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_id}' not found",
        )
    return job
