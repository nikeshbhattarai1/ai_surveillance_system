from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import WebSocket

from ai_surveillance_system.core.logger import get_logger

logger = get_logger(__name__)


class WebSocketManager:
    """
    Manages all active WebSocket connections.
    """

    def __init__(self) -> None:
        # Set gives O(1) add/remove and prevents duplicate registration
        self._active: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    # Connection lifecycle
    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self._active.add(websocket)
        logger.info(
            f"Client connected: {_host(websocket)} | "
            f"total={len(self._active)}"
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove a connection from the active set.
        Safe to call even if the websocket was never registered
        or already removed.
        """
        self._active.discard(websocket)
        logger.info(
            f"Client disconnected: {_host(websocket)} | "
            f"total={len(self._active)}"
        )

    # Messaging
    async def broadcast(self, message: dict) -> None:
        """
        Send a JSON message to every connected client.

        Stale or closed connections are removed silently so one broken
        client does not prevent others from receiving the alert.
        """
        if not self._active:
            return

        # Snapshot the set so disconnect() during iteration is safe
        targets  = list(self._active)
        dead:  list[WebSocket] = []

        await asyncio.gather(
            *[self._send_safe(ws, message, dead) for ws in targets]
        )

        # Prune dead connections collected during broadcast
        if dead:
            async with self._lock:
                for ws in dead:
                    self._active.discard(ws)
            logger.info(
                f"Pruned {len(dead)} dead connection(s) | "
                f"total={len(self._active)}"
            )

    async def send_to(
        self,
        websocket: WebSocket,
        message:   dict,
    ) -> bool:
        """
        Send a JSON message to one specific client.
        Returns True if sent successfully, False if the connection is dead.
        """
        dead: list[WebSocket] = []
        await self._send_safe(websocket, message, dead)

        if dead:
            self.disconnect(websocket)
            return False
        return True

    # Properties
    @property
    def active_connections(self) -> int:
        return len(self._active)

    # Internal helpers
    @staticmethod
    async def _send_safe(
        websocket: WebSocket,
        message:   dict,
        dead:      list[WebSocket],
    ) -> None:
        """
        Attempt to send a message; append to dead list on any failure.
        Never raises — keeps broadcast() running for remaining clients.
        """
        try:
            await websocket.send_json(message)
        except Exception as exc:
            logger.warning(
                f"Failed to send to {_host(websocket)}: {exc} — "
                f"marking as dead."
            )
            dead.append(websocket)


def _host(websocket: WebSocket) -> str:
    """Safe hostname extraction — client may be None in tests."""
    return websocket.client.host if websocket.client else "unknown"


# Module-level singleton — import this in stream.py
ws_manager = WebSocketManager()