import uuid
import aiofiles
from pathlib import Path

from fastapi import UploadFile, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.models import VideoJob, VideoStatus

settings = get_settings()
logger = get_logger(__name__)


class VideoService:
    """
    Handles all video file operations.
    """

    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

    async def validate_and_save(
        self, file: UploadFile, db: AsyncSession
    ) -> VideoJob:
        """
        Validates extension, streams file to disk, creates DB job record
        """
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        original_filename = Path(file.filename).name

        suffix = Path(file.filename).suffix.lower()
        if suffix not in self.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=f"Unsupported media type '{suffix}', allowed extensions {self.ALLOWED_EXTENSIONS}"
            )

        settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        job_id = str(uuid.uuid4())
        save_path = settings.UPLOAD_DIR / f"{job_id}{suffix}"
        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

        total_size = 0
        size_exceeded = False

        try:
            async with aiofiles.open(save_path, "wb") as out_file:
                while chunk := await file.read(1024 * 1024):

                    if total_size + len(chunk) > max_bytes:
                        size_exceeded = True
                        break

                    total_size += len(chunk)
                    await out_file.write(chunk)

        except HTTPException:
            raise
        except Exception as e:
            save_path.unlink(missing_ok=True)
            logger.error(f"File write failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save file")
        finally:
            # close the upload stream
            await file.close()

        if size_exceeded:
            save_path.unlink(missing_ok=True)
            logger.warning(
                f"Uploaded rejected: exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
            )
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds size limit"
            )

        # rejects the empty file
        if total_size == 0:
            save_path.unlink(missing_ok=True)
            raise HTTPException(
                status_code=400,
                detail="Empty file uploaded"
            )

        # Get the generated job ID without committing yet
        job = VideoJob(
            id=job_id,
            original_filename=original_filename,
            stored_path=str(save_path),
            file_size_bytes=total_size,
            status=VideoStatus.QUEUED
        )
        db.add(job)
        await db.flush()
        await db.refresh(job)

        logger.info(
            f"VideoJob created: id={job_id}, size={total_size / 1024:.1f}KB, "
            f"file={original_filename}"
        )
        return job

    async def get_job(self, job_id: str, db: AsyncSession) -> VideoJob | None:
        result = await db.execute(
            select(VideoJob).where(VideoJob.id == job_id)
        )

        return result.scalar_one_or_none()

    async def update_status(
            self,
            job_id: str,
            new_status: VideoStatus,
            db: AsyncSession,
            error_message: str | None = None
    ) -> None:
        """
        Updates job status in-place. Called by the Celery Workers.
        """
        job = await self.get_job(job_id, db)
        if not job:
            logger.error(f"update_status called on missing job: {job_id}")
            raise ValueError(f"VideoJob {job_id} not found")

        job.status = new_status
        if error_message:
            job.error_message = error_message
        await db.flush()
        logger.info(f"VideoJob {job_id} → {new_status}")

video_service = VideoService()
