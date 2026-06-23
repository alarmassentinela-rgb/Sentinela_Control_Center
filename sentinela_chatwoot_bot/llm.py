"""Cliente LLM síncrono (OpenRouter) — mismo proveedor que el bot OpenClaw."""

import logging

import httpx

import config

logger = logging.getLogger("chatwoot_bot.llm")


def chat_completion(messages: list[dict], max_tokens: int = 800,
                    temperature: float = 0.4, json_mode: bool = False) -> str:
    """Llama a OpenRouter chat/completions. Devuelve el texto o '' si falla.
    json_mode=True fuerza salida JSON (response_format), clave para que el modelo
    no pierda el formato a lo largo de la conversación."""
    if not config.OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY no configurada")
        return ""
    body = {"model": config.OPENROUTER_MODEL, "messages": messages,
            "max_tokens": max_tokens, "temperature": temperature}
    if json_mode:
        body["response_format"] = {"type": "json_object"}
    try:
        r = httpx.post(
            f"{config.OPENROUTER_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
                     "Content-Type": "application/json"},
            json=body,
            timeout=45.0,
        )
        if r.status_code != 200:
            logger.error("OpenRouter HTTP %d: %s", r.status_code, r.text[:300])
            return ""
        choices = r.json().get("choices", [])
        return choices[0].get("message", {}).get("content", "").strip() if choices else ""
    except Exception as e:
        logger.error("OpenRouter error: %s", e)
        return ""
