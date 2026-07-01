"""
WebSocket Connection Manager
Gestiona conexiones de jugadores y espectadores por round_id.
"""
import json
from typing import Dict, Set
from fastapi import WebSocket


class RoundConnectionManager:
    def __init__(self):
        # round_id -> set de WebSocket activos
        self._rooms: Dict[str, Set[WebSocket]] = {}

    def _get_room(self, round_id: str) -> Set[WebSocket]:
        if round_id not in self._rooms:
            self._rooms[round_id] = set()
        return self._rooms[round_id]

    async def connect(self, round_id: str, ws: WebSocket, accept: bool = True) -> None:
        if accept:
            await ws.accept()
        self._get_room(round_id).add(ws)

    def disconnect(self, round_id: str, ws: WebSocket) -> None:
        room = self._rooms.get(round_id, set())
        room.discard(ws)
        if not room:
            self._rooms.pop(round_id, None)

    async def broadcast_to_round(self, round_id: str, message: dict) -> None:
        room = self._rooms.get(round_id, set())
        dead: list[WebSocket] = []
        payload = json.dumps(message)
        for ws in room:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            room.discard(ws)

    async def send_to(self, ws: WebSocket, message: dict) -> None:
        await ws.send_text(json.dumps(message))


manager = RoundConnectionManager()
