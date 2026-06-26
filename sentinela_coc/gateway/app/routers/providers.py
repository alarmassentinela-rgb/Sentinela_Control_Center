# -*- coding: utf-8 -*-
"""Observabilidad del proveedor OTP: health + métricas (W5 EvoApi)."""
from fastapi import APIRouter, Depends, Response

from .. import deps
from ..metrics import metrics

router = APIRouter(tags=["infra"])


@router.get("/v1/providers/health")
def provider_health(provider=Depends(deps.get_otp_provider)):
    return provider.health()


@router.get("/metrics")
def metrics_endpoint():
    return Response(metrics.prometheus(), media_type="text/plain; version=0.0.4")
