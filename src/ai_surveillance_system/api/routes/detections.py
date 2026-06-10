from typing import Optional

from fastapi import APIRouter, Query, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.schemas.detection import DetectionListResponse, DetectionResponse
from ai_surveillance_system.services.detection_service import detection_service

router = APIRouter(prefix="/api/v1", tags=["Detections"])


@router.get(
    "/detections",
    response_model=DetectionListResponse,
    summary="List all detection events",
)
async def get_detections(
    job_id: Optional[str] = Query(None, description="Filter by video job ID"),
    event_type: Optional[str] = Query(
        None, description="Filter by event type (e.g. 'violence')"),
    limit: int = Query(50, ge=1, le=500, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
):
    total, items = await detection_service.get_detections(
        db,
        job_id=job_id,
        event_type=event_type,
        limit=limit,
        offset=offset,
    )
    return DetectionListResponse(
        total=total,
        items=items,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/detections/{detection_id}",
    response_model=DetectionResponse,
    summary="Get a single detection event by ID",
)
async def get_detection(
    detection_id: str,
    db: AsyncSession = Depends(get_db),
):
    event = await detection_service.get_detection_by_id(detection_id, db)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Detection '{detection_id}' not found",
        )
    return event
