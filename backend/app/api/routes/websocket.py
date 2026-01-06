"""
WebSocket endpoints for real-time bidirectional communication.

This module provides WebSocket support for:
- Intervention responses (faster than HTTP POST)
- Real-time session synchronization across tabs
- Typing indicators (future)
- Real-time collaboration features (future)
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import asyncio
from datetime import datetime

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """
    Manages WebSocket connections for real-time communication.

    Supports:
    - Per-session connections (for chat interactions)
    - Global connections (for session sync across tabs)
    """

    def __init__(self):
        # session_id -> set of WebSocket connections
        self.session_connections: dict[str, set[WebSocket]] = {}
        # None -> set of global connections (session sync)
        self.global_connections: set[WebSocket] = set()
        # connection -> session_id mapping
        self.connection_sessions: dict[WebSocket, Optional[str]] = {}

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.connection_sessions[websocket] = session_id

        if session_id:
            if session_id not in self.session_connections:
                self.session_connections[session_id] = set()
            self.session_connections[session_id].add(websocket)
        else:
            self.global_connections.add(websocket)

        print(
            f"[WebSocket] Connected: session={session_id}, total_connections={len(self.connection_sessions)}"
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        session_id = self.connection_sessions.pop(websocket, None)

        if session_id and session_id in self.session_connections:
            self.session_connections[session_id].discard(websocket)
            if not self.session_connections[session_id]:
                del self.session_connections[session_id]

        self.global_connections.discard(websocket)

        print(
            f"[WebSocket] Disconnected: session={session_id}, total_connections={len(self.connection_sessions)}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a message to a specific WebSocket connection."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            print(f"[WebSocket] Error sending personal message: {e}")

    async def broadcast_to_session(self, session_id: str, message: dict):
        """Broadcast a message to all connections for a specific session."""
        if session_id not in self.session_connections:
            return

        disconnected = set()
        for connection in self.session_connections[session_id]:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"[WebSocket] Error broadcasting to session: {e}")
                disconnected.add(connection)

        # Clean up disconnected connections
        for conn in disconnected:
            self.disconnect(conn)

    async def broadcast_global(self, message: dict):
        """Broadcast a message to all global connections (session sync)."""
        disconnected = set()
        for connection in self.global_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                print(f"[WebSocket] Error broadcasting global: {e}")
                disconnected.add(connection)

        for conn in disconnected:
            self.disconnect(conn)

    def get_connection_count(self, session_id: Optional[str] = None) -> int:
        """Get the number of connections for a session or globally."""
        if session_id:
            return len(self.session_connections.get(session_id, set()))
        return len(self.global_connections)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time chat communication.

    This endpoint handles:
    - Intervention actions (retry, skip, abort)
    - Real-time status updates
    - Heartbeat/keepalive

    Message Types:
    - ping/pong: Heartbeat for connection keepalive
    - intervention_action: User intervention (retry, skip, abort)
    - action_confirmation: Server confirmation of intervention action
    - intervention_state: Current intervention state
    """
    await manager.connect(websocket, session_id)

    try:
        while True:
            try:
                # Wait for client messages
                data = await websocket.receive_text()
                message = json.loads(data)

                message_type = message.get("type")
                payload = message.get("payload", {})
                timestamp = message.get("timestamp", datetime.now().isoformat())

                print(
                    f"[WebSocket] Received: type={message_type}, session={session_id}"
                )

                # Handle different message types
                if message_type == "ping":
                    # Respond with pong
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "payload": {},
                            "timestamp": datetime.now().isoformat(),
                        },
                        websocket,
                    )

                elif message_type == "intervention_action":
                    # Handle intervention action (retry, skip, abort)
                    action = payload.get("action")
                    reason = payload.get("reason")

                    print(f"[WebSocket] Intervention action: {action}")

                    # TODO: Process intervention through the agent system
                    # For now, acknowledge the action
                    await manager.send_personal_message(
                        {
                            "type": "action_confirmation",
                            "payload": {
                                "action": action,
                                "success": True,
                                "session_id": session_id,
                            },
                            "timestamp": datetime.now().isoformat(),
                        },
                        websocket,
                    )

                    # Broadcast intervention state update to all session connections
                    await manager.broadcast_to_session(
                        session_id,
                        {
                            "type": "intervention_state",
                            "payload": {
                                "awaiting_response": False,
                                "pending_error": None,
                                "available_actions": [],
                            },
                            "timestamp": datetime.now().isoformat(),
                        },
                    )

                else:
                    # Unknown message type
                    print(f"[WebSocket] Unknown message type: {message_type}")

                    await manager.send_personal_message(
                        {
                            "type": "error",
                            "payload": {
                                "message": f"Unknown message type: {message_type}"
                            },
                            "timestamp": datetime.now().isoformat(),
                        },
                        websocket,
                    )

            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {
                        "type": "error",
                        "payload": {"message": "Invalid JSON message"},
                        "timestamp": datetime.now().isoformat(),
                    },
                    websocket,
                )

    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected: session={session_id}")
    except Exception as e:
        print(f"[WebSocket] Error: {e}")
    finally:
        manager.disconnect(websocket)


@router.websocket("")
async def websocket_global(websocket: WebSocket):
    """
    Global WebSocket endpoint for session synchronization across tabs.

    This endpoint handles:
    - Session created/updated/deleted events
    - Message added events
    - Multi-tab synchronization
    """
    await manager.connect(websocket, None)

    try:
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                message_type = message.get("type")
                payload = message.get("payload", {})

                print(f"[WebSocket] Global message: type={message_type}")

                if message_type == "ping":
                    await manager.send_personal_message(
                        {
                            "type": "pong",
                            "payload": {},
                            "timestamp": datetime.now().isoformat(),
                        },
                        websocket,
                    )

                elif (
                    message_type.startswith("session_")
                    or message_type == "message_added"
                ):
                    # Broadcast session events to all global connections
                    await manager.broadcast_global(
                        {
                            "type": message_type,
                            "payload": payload,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )

            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        print("[WebSocket] Global client disconnected")
    except Exception as e:
        print(f"[WebSocket] Global error: {e}")
    finally:
        manager.disconnect(websocket)


@router.get("/status/{session_id}")
async def websocket_status(session_id: str):
    """Get WebSocket connection status for a session."""
    return {
        "session_id": session_id,
        "connection_count": manager.get_connection_count(session_id),
        "connected": session_id in manager.session_connections,
    }


@router.get("/status")
async def websocket_global_status():
    """Get global WebSocket connection status."""
    return {
        "global_connection_count": manager.get_connection_count(None),
        "active_sessions": list(manager.session_connections.keys()),
    }
