import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["Stream"])

# WebSocket payload schemas


class FramePayload(BaseModel):
    """
    Client -> Server: Video frame for processing
    """
    frame: str  # Base64-encoded JPEG/PNG


class DetectionEvent(BaseModel):
    """
    Server -> Client: Detection result
    """
    event: str
    frame_id: int
    confidence: float | None = None
    label: str | None = None
    message: str | None = None


@router.websocket("/ws/stream")
async def websocket_stream(websocket: WebSocket):
    """
    WebSocket endpoint for real-time stream processing.
    """
    await websocket.accept()
    client_host = websocket.client.host if websocket.client else "unknown"
    logger.info(f"WebSocket connected: {client_host}")

    frame_count = 0

    try:
        while True:
            # Receive and validate frame data
            try:
                raw_data = await websocket.receive_json()
            except Exception:
                await websocket.send_json({
                    "event": "error",
                    "message": "Invalid JSON format"
                })
                continue

            try:
                payload = FramePayload(**raw_data)
            except ValidationError as e:
                msg = e.errors()[0]['msg'] if e.errors() else "Invalid payload"
                await websocket.send_json({
                    "event": "error",
                    "message": f"Invalid payload: {msg}"
                })
                continue

            frame_count += 1

            # TODO: Connect ML inference pipeline here

            # Heartbeat every 30 frames
            if frame_count % 30 == 0:
                heartbeat = DetectionEvent(
                    event="heartbeat",
                    frame_id=frame_count,
                    message=f"{frame_count} frames processed."
                )
                await websocket.send_json(heartbeat.model_dump())

    except WebSocketDisconnect:
        logger.info(
            f"WebSocket Disconnected: {client_host} after {frame_count} frames.")
    except Exception as exc:
        logger.error(
            f"Websocket error from {client_host}: {exc}", exc_info=True)
        await websocket.close(code=1011)  # 1011 = internal error
