"""
Hologram WebSocket Router

Relays hand tracking data from the 'tracker' (Python script) 
to the 'display' (Mobile Web UI) in real-time.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json

router = APIRouter()

class HologramCommand(BaseModel):
    type: str
    data: Dict[str, Any]

class ConnectionManager:
    def __init__(self):
        # We might have multiple displays (e.g. testing on laptop + phone)
        self.display_connections: List[WebSocket] = []
        # We usually only have one tracker, but list is fine
        self.tracker_connections: List[WebSocket] = []
        # State persistence
        # Default to None so screen is empty until generation
        self.last_model_url: str = None

    async def connect_display(self, websocket: WebSocket):
        await websocket.accept()
        self.display_connections.append(websocket)
        print(f"[WS] Display connected. Total: {len(self.display_connections)}")
        
        # Send last model if available
        if self.last_model_url:
            import json
            print(f"[WS] Sending stored model to new client: {self.last_model_url}")
            msg = json.dumps({"type": "load_model", "url": self.last_model_url})
            await websocket.send_text(msg)

    async def connect_tracker(self, websocket: WebSocket):
        await websocket.accept()
        self.tracker_connections.append(websocket)
        print(f"[WS] Tracker connected. Total: {len(self.tracker_connections)}")
        await self.broadcast_to_displays(json.dumps({"type": "status", "msg": "Tracker Connected"}))

    def disconnect_display(self, websocket: WebSocket):
        if websocket in self.display_connections:
            self.display_connections.remove(websocket)
            print("[WS] Display disconnected.")

    def disconnect_tracker(self, websocket: WebSocket):
        if websocket in self.tracker_connections:
            self.tracker_connections.remove(websocket)
            print("[WS] Tracker disconnected.")
            # We can't await here easily as it's not async in the manager usually called from endpoint
            # But in the endpoint it is called.
            # actually broadcast_to_displays is async, so we need to be careful.
            # We will handle the broadcast in the endpoint, not here, or make this async.

    async def broadcast_to_displays(self, message: str):
        """Send data from tracker to all connected displays."""
        if not self.display_connections:
            # Only print this once every few seconds to avoid spam, or just use a counter
            # For debugging now, spam is fine, user needs to see it.
            # print("[WS] WARNING: Tracker sending data but NO DISPLAYS connected!")
            return

        # print(f"[WS-DEBUG] Broadcasting to {len(self.display_connections)} displays")
        for connection in self.display_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"[WS] Error broadcasting: {e}")
                # We could remove dead connections here, but disconnect() usually handles it
                
manager = ConnectionManager()

@router.websocket("/ws/hologram/{client_type}")
async def websocket_endpoint(websocket: WebSocket, client_type: str):
    """
    client_type: 'display' | 'tracker'
    """
    print(f"[WS-RAW] Connection attempt: {client_type}")
    import traceback
    try:
        if client_type == "display":
            await manager.connect_display(websocket)
            try:
                while True:
                    # Displays don't typically send data, but we keep connection open
                    await websocket.receive_text() 
            except WebSocketDisconnect:
                manager.disconnect_display(websocket)
                
        elif client_type == "tracker":
            await manager.connect_tracker(websocket)
            try:
                while True:
                    data = await websocket.receive_text()
                    # Relay immediately to all displays
                    await manager.broadcast_to_displays(data)
            except WebSocketDisconnect:
                manager.disconnect_tracker(websocket)
                await manager.broadcast_to_displays(json.dumps({"type": "status", "msg": "Tracker Disconnected"}))
                
    except Exception as e:
        print(f"[WS] CRITICAL ERROR in endpoint: {e}")
        traceback.print_exc()
        # Try to close if still open
        try:
            await websocket.close()
        except:
            pass

@router.post("/hologram/broadcast")
async def broadcast_command(command: HologramCommand):
    """
    Allow external services (like Celery) to send commands to the display.
    """
    import json
    # Construct message matching the format expected by hologram.html
    # content: { "type": "...", "url": "..." }
    # We flatten command.data into the root message for simplicity in JS
    message_dict = {"type": command.type}
    message_dict.update(command.data)
    
    # Save state if it's a load command
    if command.type == "load_model" and "url" in command.data:
        manager.last_model_url = command.data["url"]
    
    await manager.broadcast_to_displays(json.dumps(message_dict))
    return {"status": "broadcasted"}
