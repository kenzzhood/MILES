"""
Hologram WebSocket Router

Relays hand tracking data from the UDP tracker (Python script on port 5052)
to the 'display' (Browser tab) in real-time via WebSocket.
"""

import asyncio
import json
from typing import List, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter()

UDP_HOST = "127.0.0.1"
UDP_PORT = 5052


class HologramCommand(BaseModel):
    type: str
    data: Dict[str, Any]


class ConnectionManager:
    def __init__(self):
        self.display_connections: List[WebSocket] = []
        # State persistence — default None until generation
        self.last_model_url: str = None

    async def connect_display(self, websocket: WebSocket):
        await websocket.accept()
        self.display_connections.append(websocket)
        print(f"[WS] Display connected. Total: {len(self.display_connections)}")

        # Send last model URL to new client if available
        if self.last_model_url:
            msg = json.dumps({"type": "load_model", "url": self.last_model_url})
            print(f"[WS] Sending stored model to new client: {self.last_model_url}")
            await websocket.send_text(msg)

    def disconnect_display(self, websocket: WebSocket):
        if websocket in self.display_connections:
            self.display_connections.remove(websocket)
            print("[WS] Display disconnected.")

    async def broadcast_to_displays(self, message: str):
        """Send data to all connected display clients."""
        dead = []
        for connection in self.display_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WS] Error broadcasting to display: {e}")
                dead.append(connection)
        for d in dead:
            self.disconnect_display(d)


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# UDP → WebSocket Bridge
# ---------------------------------------------------------------------------

class UDPHandTrackerProtocol(asyncio.DatagramProtocol):
    """Asyncio UDP protocol that relays each datagram to all WS displays."""

    def connection_made(self, transport):
        self.transport = transport
        print(f"[UDP] Listening for hand-tracker data on {UDP_HOST}:{UDP_PORT}")

    def datagram_received(self, data: bytes, addr):
        message = data.decode("utf-8", errors="replace").strip()
        # Only relay non-empty packets
        if message:
            # Schedule coroutine on the running event loop (thread-safe)
            loop = asyncio.get_event_loop()
            loop.create_task(manager.broadcast_to_displays(message))

    def error_received(self, exc):
        print(f"[UDP] Error: {exc}")

    def connection_lost(self, exc):
        print(f"[UDP] Connection lost: {exc}")


async def start_udp_listener():
    """Create the asyncio UDP endpoint. Called once at app startup."""
    loop = asyncio.get_event_loop()
    await loop.create_datagram_endpoint(
        UDPHandTrackerProtocol,
        local_addr=(UDP_HOST, UDP_PORT)
    )
    print(f"[UDP] ✓ Bridge running on {UDP_HOST}:{UDP_PORT}")


# ---------------------------------------------------------------------------
# WebSocket endpoint for display clients
# ---------------------------------------------------------------------------

@router.websocket("/ws/hologram/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    """
    client_type: 'display'  — browser tab showing the 3D model
    (Tracker now sends UDP, not WebSocket.)
    """
    print(f"[WS-RAW] Connection attempt: {client_type}")
    import traceback
    try:
        if client_type == "display":
            await manager.connect_display(websocket)
            try:
                while True:
                    # Keep connection alive; displays don't send data
                    await websocket.receive_text()
            except WebSocketDisconnect:
                manager.disconnect_display(websocket)

        # Legacy tracker WebSocket path still supported for backward compat
        elif client_type == "tracker":
            await websocket.accept()
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.broadcast_to_displays(data)
            except WebSocketDisconnect:
                pass

    except Exception as e:
        print(f"[WS] CRITICAL ERROR in endpoint: {e}")
        traceback.print_exc()
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# HTTP endpoint for Celery / external services
# ---------------------------------------------------------------------------

@router.post("/hologram/broadcast")
async def broadcast_command(command: HologramCommand):
    """Allow external services (like Celery) to send commands to the display."""
    message_dict = {"type": command.type}
    message_dict.update(command.data)

    if command.type == "load_model" and "url" in command.data:
        manager.last_model_url = command.data["url"]

    await manager.broadcast_to_displays(json.dumps(message_dict))
    return {"status": "broadcasted"}
