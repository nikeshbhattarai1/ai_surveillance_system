from fastapi import APIRouter, UploadFile, File, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.db.models import VideoStatus
from ai_surveillance_system.schemas.video import UploadResponse
from ai_surveillance_system.services.video_service import video_service

router = APIRouter(prefix="/api/v1", tags=["Upload"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a video for analysis",
    description="Streams the file to disk, creates a job record, and queues processing.",
)
async def upload_video(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    job = await video_service.validate_and_save(file, db)

    # TODO Step 3: enqueue Celery task

    return UploadResponse(
        job_id=job.id,
        filename=job.original_filename,
        size_kb=round(job.file_size_bytes / 1024, 2),
        status=VideoStatus.QUEUED,
        message="Video accepted. Use job_id to track progress.",
    )
