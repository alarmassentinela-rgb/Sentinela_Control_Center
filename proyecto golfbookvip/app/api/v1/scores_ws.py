"""
WebSocket endpoint: scoring en tiempo real y modo espectador.

Conectar:  ws://host/api/v1/ws/rounds/{round_id}
Primer mensaje requerido: {"action":"auth","token":"<access_token>"}
Mensajes entrantes (jugador):
  {"action": "ping"}
  {"action": "score", "hole": 5, "gross": 4, "putts": 2}

Mensajes salientes:
  {"event": "connected", "round_id": "...", "role": "player"|"spectator"}
  {"event": "score_update", ...}
  {"event": "pong"}
  {"event": "error", "detail": "..."}
"""
import asyncio
import json
import uuid
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from jose import JWTError

from app.core.security import decode_token
from app.core.database import AsyncSessionLocal
from app.models.round import Round, RoundPlayer, RoundSpectator
from app.services.ws_manager import manager

router = APIRouter()


async def _authenticate(token: str) -> str | None:
    """Valida el token JWT y retorna el user_id, o None si inválido."""
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload.get("sub")
    except JWTError:
        return None


@router.websocket("/rounds/{round_id}")
async def round_ws(
    ws: WebSocket,
    round_id: uuid.UUID,
):
    await ws.accept()
    try:
        raw_auth = await asyncio.wait_for(ws.receive_text(), timeout=10)
        auth_msg = json.loads(raw_auth)
    except (asyncio.TimeoutError, json.JSONDecodeError):
        await ws.close(code=4001, reason="Auth requerida")
        return

    if auth_msg.get("action") != "auth":
        await ws.close(code=4001, reason="Auth requerida")
        return

    token = auth_msg.get("token")
    if not token:
        await ws.close(code=4001, reason="Token inválido")
        return

    user_id = await _authenticate(token)
    if not user_id:
        await ws.close(code=4001, reason="Token inválido")
        return

    async with AsyncSessionLocal() as db:
        # Verificar que la jugada existe y está activa
        round_result = await db.execute(select(Round).where(Round.id == round_id))
        round_ = round_result.scalar_one_or_none()
        if not round_ or round_.status not in ("active", "scheduled"):
            await ws.close(code=4004, reason="Jugada no disponible")
            return

        # Determinar rol
        player_result = await db.execute(
            select(RoundPlayer).where(
                RoundPlayer.round_id == round_id,
                RoundPlayer.user_id == user_id,
            )
        )
        is_player = player_result.scalar_one_or_none() is not None
        role = "player" if is_player else "spectator"

        # Registrar espectador en BD
        if not is_player:
            existing = await db.execute(
                select(RoundSpectator).where(
                    RoundSpectator.round_id == round_id,
                    RoundSpectator.user_id == user_id,
                )
            )
            if not existing.scalar_one_or_none():
                db.add(RoundSpectator(round_id=round_id, user_id=user_id))
                await db.commit()

    await manager.connect(str(round_id), ws, accept=False)
    await manager.send_to(ws, {"event": "connected", "round_id": str(round_id), "role": role})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_to(ws, {"event": "error", "detail": "JSON inválido"})
                continue

            action = msg.get("action")

            if action == "ping":
                await manager.send_to(ws, {"event": "pong"})

            elif action == "score" and is_player:
                # Delegamos al endpoint REST para mantener lógica centralizada
                # El cliente también puede usar POST /rounds/{id}/scores
                await manager.send_to(ws, {
                    "event": "info",
                    "detail": "Usa POST /api/v1/rounds/{round_id}/scores para registrar scores",
                })

            else:
                await manager.send_to(ws, {"event": "error", "detail": f"Acción desconocida: {action}"})

    except WebSocketDisconnect:
        manager.disconnect(str(round_id), ws)

        # Marcar left_at del espectador
        if not is_player:
            async with AsyncSessionLocal() as db:
                from datetime import datetime, timezone
                spec_result = await db.execute(
                    select(RoundSpectator).where(
                        RoundSpectator.round_id == round_id,
                        RoundSpectator.user_id == user_id,
                    )
                )
                spec = spec_result.scalar_one_or_none()
                if spec:
                    spec.left_at = datetime.now(timezone.utc)
                    await db.commit()
