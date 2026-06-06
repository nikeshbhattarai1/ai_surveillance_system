import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    String, Float, Boolean, DateTime, Text,
    Integer, ForeignKey, Enum as SAEum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from ai_surveillance_system.db.session import Base


class VideoStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, enum.Enum):
    VIOLENCE = "violence"
    ANOMALY = "anomaly"
    INTRUSION = "intrusion"
    FIRE = "fire"
    UNKNOWN = "unknown"


class VideoJob(Base):
    """
    Represents video uploaded for analysis.
    """
    __tablename__ = "video_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[VideoStatus] = mapped_column(
        SAEum(VideoStatus), default=VideoStatus.QUEUED, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
                                                 default=lambda: datetime.now(
                                                     timezone.utc),
                                                 onupdate=lambda: datetime.now(
                                                     timezone.utc),
                                                 nullable=False)
    detections: Mapped[list["DetectionEvent"]] = relationship(
        "DetectionEvent", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<VideoJob id={self.id} status={self.status}>"


class DetectionEvent(Base):
    """
    A single security event detected in a video or live stream.
    null job_id means the event came from a live WebSocket stream.
    """
    __tablename__ = "detection_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        nullable=False,
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    job_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("video_jobs.id", ondelete="CASCADE"),
        nullable=True
    )
    event_type: Mapped[EventType] = mapped_column(
        SAEum(EventType), nullable=False,
        default=EventType.UNKNOWN
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    frame_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True
    )
    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    notified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False)
    notification_channel: Mapped[str | None] = mapped_column(
        String(50), nullable=True)
    notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True)
    source: Mapped[str] = mapped_column(
        String(32), default="upload", nullable=False)

    job: Mapped["VideoJob | None"] = relationship(
        "VideoJob", back_populates="detections"
    )

    # Index filter/sort columns used by get_detections() to avoid full table scans.
    __table_args__ = (
        Index("idx_detection_job_id", "job_id"),
        Index("idx_detection_event_type", "event_type"),
        Index("idx_detection_timestamp", "timestamp"),
    )

    def __repr__(self):
        return f"<DetectionEvent id={self.id} type={self.event_type} conf={self.confidence:.2f}>"
