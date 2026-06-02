import uuid
import aiofiles
from pathlib import Path
from datetime import datetime, timezone

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from fastapi.responses import JSONResponse

from ai_surveillance_system.core.config import get_settings, Settings
from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Upload"])

ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


@router.post(
    "/upload",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a video for analysis",
    description="Upload accepted, processing queued."
)
async def upload_video(
    file: UploadFile = File(...),
    settings: Settings = Depends(get_settings)
):
    """
    Accepts a video file for security analysis.
    """

    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        logger.warning(f"Rejected upload: invalid extension '{suffix}'")
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    chunk_size = 1024 * 1024  # 1 MB

    job_id = str(uuid.uuid4())
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    save_path = settings.UPLOAD_DIR / f"{job_id}{suffix}"

    total_size = 0
    size_exceeded = False

    try:
        async with aiofiles.open(save_path, "wb") as out_file:
            while chunk := await file.read(chunk_size):

                # enforce limit before writing
                if total_size + len(chunk) > max_bytes:
                    size_exceeded = True
                    break

                total_size += len(chunk)
                await out_file.write(chunk)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save upload: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save file. Please try again."
        )

    finally:
        # close upload stream
        await file.close()

    if size_exceeded:
        save_path.unlink(missing_ok=True)
        logger.warning(
            f"Upload rejected: exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit."
        )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
        )

    # reject empty file
    if total_size == 0:
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=400,
            detail="Empty file uploaded"
        )

    logger.info(
        f"Uploaded file: job_id={job_id}, size={total_size / 1024:.1f}KB, file={file.filename}"
    )

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job_id,
            "filename": file.filename,
            "size_kb": round(total_size / 1024, 2),
            "status": "queued",
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "message": "Video accepted for processing. Use job_id to track progress."
        }
    )