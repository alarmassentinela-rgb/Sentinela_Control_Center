import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import CurrentUser, DB
from app.core.config import settings

router = APIRouter()


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    round_id: Optional[str] = None
    locale: str = "es"


def _build_system_prompt(user, stats, round_info, locale: str) -> str:
    lang = "Responde siempre en español, a menos que el usuario escriba en inglés." \
        if locale == "es" else \
        "Always respond in English unless the user writes in Spanish."

    hcp = f"{user.handicap_index:.1f}" if user.handicap_index is not None else "No registrado"

    stats_block = ""
    if stats:
        avg = f"{stats.avg_score:.1f}" if stats.avg_score else "N/A"
        gir = f"{stats.gir_pct:.0f}%" if stats.gir_pct else "N/A"
        putts = f"{stats.avg_putts_per_round:.1f}" if stats.avg_putts_per_round else "N/A"
        stats_block = f"""
Estadísticas del jugador:
- Rondas totales: {stats.total_rounds}
- Score promedio: {avg}
- GIR%: {gir}
- Putts por ronda: {putts}
- Mejores diferencial: {f"{stats.best_differential:.1f}" if stats.best_differential else "N/A"}
- Birdies totales: {stats.total_birdies}
- Eagles totales: {stats.total_eagles}"""

    round_block = ""
    if round_info:
        round_block = f"""
Ronda en curso:
- Nombre: {round_info.get('name', 'Sin nombre')}
- Cancha: {round_info.get('course_name', 'No especificada')}
- Formato: {round_info.get('game_format', 'stroke')}
- Hoyos: {round_info.get('holes_to_play', 18)}"""

    return f"""Eres CaddyAI, el asistente inteligente de GolfBookVIP. Eres un caddie experto con profundo conocimiento de:
- Reglas oficiales de golf (R&A / USGA 2023)
- Estrategia y gestión de cancha (course management)
- Selección de palos según distancia, viento, lie y condiciones
- Hándicap WHS (World Handicap System)
- Técnica de swing, putting y juego corto
- Estadísticas y mejora del juego

Jugador actual:
- Nombre: {user.first_name} {user.last_name}
- Username: @{user.username}
- Hándicap Index: {hcp}
{stats_block}
{round_block}

Pautas de respuesta:
- Sé conciso y práctico, como un buen caddie en el campo
- Cuando des distancias de palos, considera que el jugador tiene HCP {hcp}
- Si te preguntan una regla, cita el artículo correspondiente cuando sea relevante
- No inventes scores ni estadísticas que no estén en el contexto
- {lang}"""


@router.post("/")
async def chat(data: ChatRequest, current_user: CurrentUser, db: DB):
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="CaddyAI no está configurado")

    # Load player stats for context
    from app.models.handicap import PlayerStats
    stats_res = await db.execute(
        select(PlayerStats).where(PlayerStats.user_id == current_user.id)
    )
    stats = stats_res.scalar_one_or_none()

    # Load current round if provided
    round_info = None
    if data.round_id:
        from app.models.round import Round
        from app.models.course import Course
        r = await db.execute(
            select(Round, Course)
            .outerjoin(Course, Course.id == Round.course_id)
            .where(Round.id == data.round_id)
        )
        row = r.first()
        if row:
            round_, course = row
            round_info = {
                "name": round_.name,
                "course_name": course.name if course else None,
                "game_format": round_.game_format,
                "holes_to_play": round_.holes_to_play,
            }

    system_prompt = _build_system_prompt(current_user, stats, round_info, data.locale)

    # Build message history for Claude
    messages = [{"role": m.role, "content": m.content} for m in data.history]
    messages.append({"role": "user", "content": data.message})

    async def generate():
        try:
            from anthropic import AsyncAnthropic
            client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

            async with client.messages.stream(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {json.dumps({'text': text})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering for SSE
        },
    )
