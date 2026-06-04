from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel

from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["Detections"])


class DetectionResponse(BaseModel):
    id: str
    job_id: str
    event_type: str
    confidence: float
    frame_path: Optional[str]
    timestamp: datetime
    notified: bool


@router.get(
    "/detections",
    response_model=list[DetectionResponse],
    summary="List all detection events.",
)
async def get_detections(
    job_id: Optional[str] = Query(None, description="Filter by video job ID"),
    event_type: Optional[str] = Query(
        None, description="Filter by event type (e.g, 'violence')"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset")
):
    """
    Returns security detection events.
    """

    # TODO: Fetch detection events from database
    raise HTTPException(status_code=501, detail="Not implemented yet")



@router.get(
    "/detections/{detection_id}",
    response_model=DetectionResponse,
    summary="Get a single detection event by ID"
)
async def get_detection(detection_id: str):
    """
    Fetch details of a single detection event.
    """

    # TODO: Fetch detection event by ID from database
    raise HTTPException(status_code=501, detail="Not implemented yet")

