"""Arnés de prueba del TRIAGE del bot (no toca Chatwoot ni clientes).

Simula conversaciones turno por turno contra el LLM real (OpenRouter) usando los
prompts nuevos de config.py, e imprime la decisión {action, topic} de cada turno.
Correr DENTRO del contenedor del bot (tiene OPENROUTER_API_KEY en el env):

    docker exec -w /tmp/bottest sentinela-chatwoot-bot python test_triage.py
"""

import json
import re

import config
import llm

SAMPLE_FICHA = """CLIENTE EN ODOO: Juan Pérez
- Suscripción SUB-0123 | Internet | Plan 20M | $400/mes | Estado: Activo | Próximo cobro: 2026-07-01 | Domicilio: Col. Centro, Matamoros
    Conexión que ve el sistema: EN LÍNEA ✅ | Señal: -62 (buena)
ADEUDO: Al corriente (sin facturas pendientes)"""


def _parse(raw: str) -> dict:
    if not raw:
        return {}
    txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.IGNORECASE).strip()
    try:
        return json.loads(txt)
    except Exception:
        m = re.search(r"\{.*\}", txt, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def run(label, verified, ficha, turns, expect):
    base = config.SYSTEM_PROMPT if verified else config.SYSTEM_PROMPT_UNVERIFIED
    system = base.format(name="Juan" if verified else "(desconocido)", ficha=ficha)
    messages = [{"role": "system", "content": system}]
    print("\n" + "=" * 78)
    print(f"ESCENARIO: {label}   (verified={verified}, esperado≈{expect})")
    print("-" * 78)
    last_action = None
    for user_msg in turns:
        messages.append({"role": "user", "content": user_msg})
        raw = llm.chat_completion(messages, json_mode=True)
        d = _parse(raw)
        action = (d.get("action") or "?").lower()
        topic = (d.get("topic") or "-")
        msg = (d.get("message") or "").replace("\n", " ")[:120]
        extra = []
        for k in ("interest", "subscription", "summary"):
            if d.get(k):
                extra.append(f"{k}={str(d[k])[:40]}")
        last_action = action
        print(f"  👤 {user_msg}")
        print(f"  🤖 [{action} / {topic}] {msg}")
        if extra:
            print(f"      ↳ {' | '.join(extra)}")
        messages.append({"role": "assistant", "content": d.get("message") or raw})
    ok = "✅" if last_action == expect else "⚠️  (revisar)"
    print(f"  RESULTADO: acción final = {last_action}  {ok}")


if __name__ == "__main__":
    print("Modelo:", config.OPENROUTER_MODEL)

    # 1) Prospecto de VENTAS, número NO registrado → debe terminar en create_lead
    run("Prospecto de ventas (nuevo)", False, "",
        ["Hola, quiero contratar internet",
         "En la colonia Buenavista, Matamoros",
         "Sí, regístralo por favor"],
        expect="create_lead")

    # 2) Cliente EXISTENTE que quiere AMPLIAR → create_lead (no reporte)
    run("Cliente existente quiere cámaras", True, SAMPLE_FICHA,
        ["Quiero contratar también cámaras de seguridad",
         "En el mismo domicilio",
         "Sí, que me contacte un asesor"],
        expect="create_lead")

    # 3) FALLA de soporte de cliente existente → diagnostica, NO ventas
    run("Falla de internet (soporte)", True, SAMPLE_FICHA,
        ["No me sirve el internet desde hoy en la mañana"],
        expect="reply")  # debe quedarse en reply diagnosticando, topic=soporte

    # 4) COBRANZA → handoff topic cobranza
    run("Quiere pagar / cobranza", True, SAMPLE_FICHA,
        ["Quiero saber cuánto debo para pagar mi servicio"],
        expect="handoff")

    # 5) Mensaje AMBIGUO → reply preguntando qué necesita (triage)
    run("Saludo ambiguo", True, SAMPLE_FICHA,
        ["Buenas tardes"],
        expect="reply")
