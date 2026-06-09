from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.models import DetectionEvent, EventType
from ai_surveillance_system.schemas.detection import DetectionCreate

settings = get_settings()
logger = get_logger(__name__)


class DetectionService:
    """
    Orchestrates the ML pipeline and persists detection results.
    """

    async def record_detection(
        self,
        data: DetectionCreate,
        db: AsyncSession,
    ) -> DetectionEvent:
        """
        Persist a detection event returned by the ML pipeline.
        """
        event = DetectionEvent(
            job_id=data.job_id,
            event_type=data.event_type,
            confidence=data.confidence,
            frame_path=data.frame_path,
            frame_number=data.frame_number,
            source=data.source,
        )

        db.add(event)
        await db.flush()
        await db.refresh(event)

        logger.info(
            f"DetectionEvent recorded: "
            f"type={event.event_type}, "
            f"conf={event.confidence:.2f}, "
            f"job={event.job_id}"
        )

        return event

    async def get_detections(
        self,
        db: AsyncSession,
        job_id: str | None = None,
        event_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[int, list[DetectionEvent]]:
        """
        Returns paginated detection events.
        """

        query = select(DetectionEvent).order_by(
            DetectionEvent.timestamp.desc()
        )

        count_query = select(func.count()).select_from(DetectionEvent)

        if job_id:
            query = query.where(
                DetectionEvent.job_id == job_id
            )
            count_query = count_query.where(
                DetectionEvent.job_id == job_id
            )

        if event_type:
            try:
                event_type_enum = EventType(event_type)
            except ValueError:
                return 0, []

            query = query.where(
                DetectionEvent.event_type == event_type_enum
            )

            count_query = count_query.where(
                DetectionEvent.event_type == event_type_enum
            )

        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        paginated_result = await db.execute(
            query.limit(limit).offset(offset)
        )

        items = paginated_result.scalars().all()

        return total, list(items)

    async def get_detection_by_id(
        self,
        detection_id: str,
        db: AsyncSession,
    ) -> DetectionEvent | None:
        """
        Fetch a single detection event by ID.
        """
        result = await db.execute(
            select(DetectionEvent).where(
                DetectionEvent.id == detection_id
            )
        )

        return result.scalar_one_or_none()

    async def mark_notified(
        self,
        detection_id: str,
        channel: str,
        db: AsyncSession,
    ) -> None:
        """
        Mark a detection event as notified.
        """
        event = await self.get_detection_by_id(
            detection_id,
            db,
        )

        if event:
            event.notified = True
            event.notification_channel = channel
            event.notified_at = datetime.now(timezone.utc)

            await db.flush()

    def should_alert(self, confidence: float) -> bool:
        """
        Only alert if confidence exceeds configured threshold.
        """
        return confidence >= settings.CONFIDENCE_THRESHOLD


detection_service = DetectionService()
