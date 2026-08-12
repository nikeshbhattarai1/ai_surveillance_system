import base64

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_surveillance_system.core.logger import get_logger
from ai_surveillance_system.db.session import get_db
from ai_surveillance_system.ml.preprocessing import StreamFrameBuffer
from ai_surveillance_system.realtime.websocket_manager import ws_manager
from ai_surveillance_system.services.detection_service import detection_service

logger = get_logger(__name__)

router = APIRouter(tags=["Stream"])

HEARTBEAT_FRAME_INTERVAL = 30


class FramePayload(BaseModel):
    """
    Client -> Server: Base64-encoded JPEG/PNG frame.
    """
    frame: str


class DetectionEvent(BaseModel):
    """
    Server -> Client: Detection result or heartbeat.
    """
    event: str
    frame_id: int
    confidence: float | None = None
    label: str | None = None
    event_type: str | None = None
    is_threat: bool | None = None
    frame_path: str | None = None
    message: str | None = None


@router.websocket("/ws/stream")
async def websocket_stream(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    await ws_manager.connect(websocket)

    client_host = websocket.client.host if websocket.client else "unknown"
    buffer = StreamFrameBuffer(overlap=0.5)
    frame_count = 0

    try:
        while True:
            # Receive
            try:
                raw_data = await websocket.receive_json()
            except Exception:
                await websocket.send_json({
                    "event":   "error",
                    "message": "Invalid JSON format.",
                })
                continue

            try:
                payload = FramePayload(**raw_data)
            except ValidationError as exc:
                msg = exc.errors()[0]["msg"] if exc.errors(
                ) else "Invalid payload"
                await websocket.send_json({
                    "event":   "error",
                    "message": f"Invalid payload: {msg}",
                })
                continue

            frame_count += 1

            # Decode base64 → bytes
            try:
                frame_bytes = base64.b64decode(payload.frame)
            except Exception:
                await websocket.send_json({
                    "event":   "error",
                    "message": f"Frame {frame_count}: invalid base64 encoding.",
                })
                continue

            # Push into rolling buffer + run inference when ready
            try:
                processed, _ = await detection_service.push_stream_frame_bytes(
                    frame_bytes=frame_bytes,
                    buffer=buffer,
                    db=db,
                    client_host=client_host,
                )
            except ValueError as exc:
                logger.warning(
                    f"Frame decode error (frame={frame_count}): {exc}")
                await websocket.send_json({
                    "event":   "error",
                    "message": f"Frame {frame_count}: could not decode image.",
                })
                continue
            except Exception as exc:
                logger.error(
                    f"Inference error (frame={frame_count}): {exc}",
                    exc_info=True,
                )
                await websocket.send_json({
                    "event":   "error",
                    "message": "Inference failed. Frame skipped.",
                })
                continue

            # Broadcast threat to all clients / send clip result to sender
            if processed is not None:
                if processed.is_threat:
                    # Threat goes to every connected client
                    await ws_manager.broadcast({
                        "event": "threat_detected",
                        "frame_id": frame_count,
                        "confidence": processed.confidence,
                        "label": processed.label,
                        "event_type": processed.event_type,
                        "is_threat": processed.is_threat,
                        "frame_path": processed.frame_paths[0] if processed.frame_paths else None,
                        "message": None,
                    })
                else:
                    # Non-threat clip result sent only to the sender
                    await ws_manager.send_to(
                        websocket,
                        {
                            "event": "clip_processed",
                            "frame_id": frame_count,
                            "confidence": processed.confidence,
                            "label": processed.label,
                            "event_type": processed.event_type,
                            "is_threat": False,
                            "frame_path": None,
                            "message": None,
                        },
                    )

            # Heartbeat
            if frame_count % HEARTBEAT_FRAME_INTERVAL == 0:
                await ws_manager.send_to(
                    websocket,
                    DetectionEvent(
                        event="heartbeat",
                        frame_id=frame_count,
                        message=(
                            f"{frame_count} frames received. "
                            f"Buffer: {buffer.buffered}/{buffer.sequence_length}."
                        ),
                    ).model_dump(),
                )

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket disconnected: {client_host} "
            f"after {frame_count} frames."
        )
        buffer.reset()

    except Exception as exc:
        logger.error(
            f"WebSocket error from {client_host}: {exc}",
            exc_info=True,
        )
        buffer.reset()
        await websocket.close(code=1011)

    finally:
        # unregister
        ws_manager.disconnect(websocket)
