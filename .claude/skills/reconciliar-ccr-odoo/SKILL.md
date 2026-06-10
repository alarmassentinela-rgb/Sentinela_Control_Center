---
name: reconciliar-ccr-odoo
description: >-
  Reconcilia el estado de clientes WISP entre el CCRsentinela (PPPoE/walled-garden)
  y Odoo sentinela_subscriptions. Úsalo cuando un cliente "active en Odoo pero
  cortado en CCR" (o al revés), para suspender un moroso, reactivar a quien pagó,
  o auditar que CCR y Odoo cuadren (N=N, sin huérfanos). Cubre el flujo
  suspensión → factura de adeudo → pago → reactivación automática.
---

# Reconciliación CCRsentinela ↔ Odoo (WISP)

Odoo (`sentinela_subscriptions`) es la fuente de verdad del estado del cliente WISP;
el CCRsentinela aplica el corte real (perfil `argusblack_servicio_suspendido` /
walled-garden, no deshabilita el secret). La migración Argus→Odoo está cerrada
(Argus ya no re-borra ni re-suspende). Detalle en memoria
`project_migracion_wisp_argus_a_odoo` y `session_04_05jun2026`.

## Caso 1 — "active en Odoo pero cortado en CCR" (o inverso)
Es desincronización. Procedimiento:
1. Identificar la sub (SUB-xxxx / cta####) y su `state` en Odoo.
2. Ver el estado real en el CCR (perfil del secret PPPoE: ¿servicio normal o
   walled-garden?).
3. Alinear al estado de Odoo: si Odoo dice `active` → el secret debe estar en perfil
   normal con su pool; si Odoo dice suspendido → walled-garden.
4. Verificar el reconteo global: `reconcile_ccr_all.py` (en repo) debe dar **N=N,
   0 huérfanos** (histórico: 109=109, 101=101). Correr SIEMPRE tras cambios para
   confirmar que no quedaron descuadres.

## Caso 2 — suspender un moroso (manual, mientras no hay factura)
La facturación automática arranca después (~1-jul); antes no hay factura → el cron
de auto-suspensión no puede actuar. Para cortar a un moroso real **hoy**:
1. Suspender la sub en Odoo (acción de suspensión → CCR a walled-garden).
2. **Generar factura de adeudo** (account.move publicada) para tener saldo sobre el
   cual aplicar el pago. (Histórico: cta0209 Yolanda/SUB-0348, cta0190 Laura/SUB-0338,
   cta0135 Mayra/SUB-0311 → INV/2026/00053-55.)
3. Esto deja al cliente listo para reactivarse automáticamente al pagar (caso 3).

## Caso 3 — reactivar a quien pagó (automático desde v.70)
Al registrar el pago de una factura ligada a una sub suspendida, el hook en
`account.move._compute_payment_state` reconecta sola (`action_reactivate` → CCR a
perfil normal). Para que el pago quede en **"Pagado"** al instante (no "En proceso"):
- Diario **HSBC** → método **"Pago manual"** → cuenta Banco (102.01.01) directo.
  El default de Odoo 18 deja pagos en `in_process` (falta conciliación bancaria) y
  NO dispara la reactivación. Verificar que el método manual esté configurado.

## Acceso / herramientas
- Odoo prod por XML-RPC o por odoo shell:
  ```bash
  ssh -p 2222 -i ~/.ssh/id_rsa_sentinela egarza@192.168.3.2 \
    'docker exec -i odoo18-migration-web-1 odoo shell -d Sentinela_V18 --no-http' < script.py
  # env.cr.commit() para persistir
  ```
- CCRsentinela: acceso API (ver memoria de red / credenciales). Suspensión =
  walled-garden, NO deshabilitar el secret (eso lo deja sin perfil de suspensión).
- Scripts en repo: `reconcile_ccr_all.py` (auditoría global).

## Salvaguardas
- Tras cualquier cambio, correr la reconciliación global (N=N) antes de declarar cerrado.
- No deshabilitar secrets PPPoE para "suspender" — usar el perfil walled-garden.
- Verificar end-to-end con rollback cuando se prueba la reactivación automática.
- Si un cliente reporta "no navega" pero Odoo+CCR están OK, sospechar red (ver
  skill diagnostico-red) antes que reconciliación — varios "no navega" fueron falsa alarma.
