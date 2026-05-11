import json
import httpx
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


async def _get_weather(city: str, country: str = "") -> Optional[dict]:
    """Fetch current weather from OpenWeatherMap. Returns None on any error."""
    if not settings.OPENWEATHER_API_KEY or not city:
        return None
    try:
        location = f"{city},{country}" if country else city
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "q": location,
                    "appid": settings.OPENWEATHER_API_KEY,
                    "units": "metric",
                    "lang": "es",
                },
            )
        if res.status_code != 200:
            return None
        d = res.json()
        wind_kmh = round(d["wind"]["speed"] * 3.6)
        wind_dir = _wind_direction(d["wind"].get("deg", 0))
        return {
            "city": d["name"],
            "temp": round(d["main"]["temp"]),
            "feels_like": round(d["main"]["feels_like"]),
            "condition": d["weather"][0]["description"].capitalize(),
            "humidity": d["main"]["humidity"],
            "wind_kmh": wind_kmh,
            "wind_dir": wind_dir,
            "gusts_kmh": round(d["wind"].get("gust", d["wind"]["speed"]) * 3.6),
        }
    except Exception:
        return None


def _wind_direction(deg: float) -> str:
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"]
    return dirs[round(deg / 22.5) % 16]


def _build_system_prompt(user, stats, round_info, weather, locale: str) -> str:
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
- Mejor diferencial: {f"{stats.best_differential:.1f}" if stats.best_differential else "N/A"}
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

    weather_block = ""
    if weather:
        weather_block = f"""
Clima actual en {weather['city']}:
- Temperatura: {weather['temp']}°C (sensación {weather['feels_like']}°C)
- Condición: {weather['condition']}
- Humedad: {weather['humidity']}%
- Viento: {weather['wind_kmh']} km/h dirección {weather['wind_dir']} (ráfagas {weather['gusts_kmh']} km/h)

Considera el clima al dar consejos de selección de palo: el viento en contra aumenta la distancia efectiva del hoyo, el viento a favor la reduce (~1 club por cada 15-20 km/h). El frío reduce la distancia de la bola (~5% por cada 10°C bajo 20°C)."""

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
{weather_block}

Pautas de respuesta:
- Sé conciso y práctico, como un buen caddie en el campo
- Cuando des distancias de palos, considera el hándicap del jugador Y el clima actual
- Si te preguntan una regla, cita el artículo cuando sea relevante
- No inventes scores ni estadísticas que no estén en el contexto
- {lang}"""


@router.post("/")
async def chat(data: ChatRequest, current_user: CurrentUser, db: DB):
    if not settings.GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="CaddyAI no está configurado")

    # Load player stats
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

    # Fetch current weather using player's city
    weather = await _get_weather(
        city=current_user.city or "",
        country=current_user.country or "",
    )

    system_prompt = _build_system_prompt(current_user, stats, round_info, weather, data.locale)

    # Build Gemini message history
    gemini_history = []
    for m in data.history:
        role = "model" if m.role == "assistant" else "user"
        gemini_history.append({"role": role, "parts": [m.content]})

    async def generate():
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)

            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=system_prompt,
            )

            chat_session = model.start_chat(history=gemini_history)

            response = await chat_session.send_message_async(
                data.message,
                stream=True,
            )

            async for chunk in response:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
