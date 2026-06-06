from datetime import datetime
from pydantic import BaseModel, Field

from ai_surveillance_system.db.models import EventType


class DetectionCreate(BaseModel):
    job_id: str | None = None
    event_type: EventType
    confidence: float = Field(..., ge=0.0, le=1.0)
    frame_path: str | None = None
    frame_number: int | None = None
    source: str = "upload"


class DetectionResponse(BaseModel):
    id: str
    job_id: str | None
    event_type: EventType
    confidence: float
    frame_path: str | None
    frame_number: int | None
    timestamp: datetime
    notified: bool
    notified_at: datetime | None
    notification_channel: str | None
    source: str

    model_config = {"from_attributes": True}


class DetectionListResponse(BaseModel):
    total: int
    items: list[DetectionResponse]
    limit: int
    offset: int
