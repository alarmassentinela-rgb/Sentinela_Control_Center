# -*- coding: utf-8 -*-
"""Normalización de teléfono a E.164 para México (único punto del gateway).

EvoApi exige el número con código de país. Si el cliente lo escribe sin +52
(uso cotidiano), WhatsApp lo rechaza (HTTP 400, exists:false) y el OTP nunca llega.
Esta función convierte cualquier formato común MX a '52' + 10 dígitos nacionales,
que es el formato que EvoApi acepta y entrega (verificado en STAGING).

Acepta: 8681255741 · 868 125 5741 · 868-125-5741 · (868)125-5741 ·
        +52 8681255741 · 52 8681255741 · 5218681255741
"""
import re

MX_CC = "52"


def to_evoapi_mx(raw: str) -> str:
    """Devuelve '52' + 10 dígitos nacionales (formato EvoApi para MX)."""
    digits = re.sub(r"\D", "", raw or "")
    if len(digits) == 13 and digits.startswith(MX_CC + "1"):
        national = digits[3:]           # 52 + 1 + 10  (formato viejo con '1')
    elif len(digits) == 12 and digits.startswith(MX_CC):
        national = digits[2:]           # 52 + 10
    elif len(digits) == 11 and digits.startswith("1"):
        national = digits[1:]           # 1 + 10 (defensivo)
    else:
        national = digits[-10:]         # 10 dígitos nacionales (o fallback)
    return MX_CC + national
