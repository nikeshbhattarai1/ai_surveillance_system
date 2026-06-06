from datetime import datetime
from pydantic import BaseModel

from ai_surveillance_system.db.models import VideoStatus


class VideoJobCreate(BaseModel):
    original_filename: str
    stored_path: str
    file_size_bytes: int


class VideoJobResponse(BaseModel):
    id: str
    original_filename: str
    file_size_bytes: int
    status: VideoStatus
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    size_kb: float
    status: VideoStatus
    uploaded_at: datetime
    message: str