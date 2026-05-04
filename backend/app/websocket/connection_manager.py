"""
connection_manager.py — FastAPI WebSocket Connection Manager

Manages all active WebSocket client connections and provides:
    - connect / disconnect lifecycle
    - broadcast to all clients (concurrent via asyncio.gather)
    - send_personal_message to a single client
    - automatic cleanup of dead connections

Singleton: ``from app.websocket.connection_manager import manager``
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Union

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Thread-safe(ish) WebSocket connection manager for FastAPI.

    Broadcast uses asyncio.gather so all clients receive the message
    concurrently — total latency ≈ slowest single client, not sum.
    """

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket) -> None:
        """Accept handshake and register the connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected — total: %d", len(self.active_connections)
        )

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection (safe to call even if already removed)."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket client disconnected — total: %d", len(self.active_connections)
        )

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def broadcast(self, message: Union[Dict[str, Any], str]) -> None:
        """
        Send a message to ALL connected clients concurrently.

        Args:
            message: dict (sent as JSON) or str (sent as text).

        Dead connections are automatically detected and removed.
        """
        if not self.active_connections:
            return

        is_dict = isinstance(message, dict)

        async def _send(ws: WebSocket) -> WebSocket | None:
            """Send to one client; return the websocket if it failed."""
            try:
                if is_dict:
                    await ws.send_json(message)
                else:
                    await ws.send_text(str(message))
                return None
            except Exception as exc:
                logger.warning("Broadcast failed for a client: %s", exc)
                return ws

        # Fire all sends concurrently
        results = await asyncio.gather(
            *[_send(ws) for ws in self.active_connections],
            return_exceptions=False,
        )

        # Clean up any dead connections returned by _send
        dead = [ws for ws in results if ws is not None]
        for ws in dead:
            self.disconnect(ws)

        if dead:
            logger.info("Removed %d dead connection(s) after broadcast", len(dead))

    async def send_personal_message(
        self,
        message:   Union[Dict[str, Any], str],
        websocket: WebSocket,
    ) -> None:
        """
        Send a message to a single specific client.

        Args:
            message:   dict (JSON) or str.
            websocket: Target WebSocket connection.
        """
        try:
            if isinstance(message, dict):
                await websocket.send_json(message)
            else:
                await websocket.send_text(str(message))
        except Exception as exc:
            logger.warning("Personal message failed: %s", exc)
            self.disconnect(websocket)

    # ── Utility ───────────────────────────────────────────────────────────────

    @property
    def connection_count(self) -> int:
        """Number of currently active connections."""
        return len(self.active_connections)

    def get_status(self) -> Dict[str, Any]:
        """Return manager status for the /health endpoint."""
        return {
            "active_connections": self.connection_count,
            "connected":          self.connection_count > 0,
        }


# ── Singleton export ──────────────────────────────────────────────────────────
manager = ConnectionManager()
