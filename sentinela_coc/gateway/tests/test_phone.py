# -*- coding: utf-8 -*-
"""Normalización E.164 MX (fix 🔴 bloqueante: OTP no llegaba sin código de país)."""
import pytest

from app.services.phone import to_evoapi_mx

CANONICAL = "528681255741"  # 52 + 10 dígitos nacionales (formato que EvoApi entrega)


@pytest.mark.parametrize(
    "raw",
    [
        "8681255741",
        "868 125 5741",
        "868-125-5741",
        "(868)125-5741",
        "+52 8681255741",
        "52 8681255741",
        "5218681255741",
        "+528681255741",
        "+52 868 125 5741",
    ],
)
def test_all_formats_normalize_to_e164_mx(raw):
    assert to_evoapi_mx(raw) == CANONICAL


def test_idempotente():
    assert to_evoapi_mx(to_evoapi_mx("868 125 5741")) == CANONICAL


def test_otro_numero():
    assert to_evoapi_mx("55 1234 5678") == "525512345678"
    assert to_evoapi_mx("+52 (55) 1234-5678") == "525512345678"
