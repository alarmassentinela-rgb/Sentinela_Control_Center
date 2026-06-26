# CRON_STATUS — Estado de tareas programadas (Sentinela)

> Documenta los crones de los módulos `sentinela_*` y su estado **intencional**. El **estado real** (`ir.cron.active`) debe verificarse en V18 (`Sentinela`), porque puede divergir del código (`noupdate`).
> ⚠️ **Freeze de facturación activo** hasta go-live ≈ 1-jul-2026: varios crones de `sentinela_subscriptions` están **OFF a propósito** en prod. No asumirlos activos.
> Creado en Sprint 0 del Portal COC (25-jun-2026). Mantener al día.

## sentinela_subscriptions
| Cron (id) | Método | Cadencia | Estado intencional | Notas |
|---|---|---|---|---|
| `ir_cron_generate_invoices` | `_cron_generate_pre_invoices` | 1 día | ⏸️ FREEZE (verificar) | Genera pre-facturas. Estreno masivo ~1-jul. |
| `ir_cron_auto_suspend_overdue` | `_cron_auto_suspend_overdue` | 1 día | ⏸️ FREEZE (verificar) | Suspensión por mora. |
| `ir_cron_send_payment_reminders` | `_cron_send_payment_reminders` | 1 día | ⏸️ FREEZE (verificar) | Recordatorios de cobranza. |
| `ir_cron_check_extensions` | `_cron_check_expired_extensions` | 1 hora | ▶️ (verificar) | Cierra prórrogas vencidas. |
| `ir_cron_check_leasing_end` | `_cron_check_leasing_end` | 1 día | ▶️ (verificar) | Fin de leasing de equipo. |
| `ir_cron_refresh_antenna_signal` | `_cron_refresh_antenna_signal` | 15 min | ▶️ (verificar) | Refresca señal/conexión WISP. |

## sentinela_monitoring
| Cron | Método | Cadencia | Estado | Notas |
|---|---|---|---|---|
| Detección de paneles offline | `_cron_detect_offline_panels` | ~1 hora | ▶️ (verificar) | Genera eventos AUTO_OFFLINE. |
| Reconciliación SentiCar | (reconcile) | 6 horas | ▶️ (verificar) | Sincroniza Traccar↔Odoo. |
| Telegram poll | `_cron_telegram_poll_updates` | minutos | ▶️ (verificar) | Captura chat_id/teléfono en /start. |

## sentinela_fsm
| Cron | Método | Cadencia | Estado | Notas |
|---|---|---|---|---|
| Mantenimiento preventivo | `_cron_generate_preventive_maintenance` | 1 día | ▶️ (verificar) | Genera órdenes de mantenimiento. |

## sentinela_syscom
| Cron | Método | Cadencia | Estado | Notas |
|---|---|---|---|---|
| `ir_cron_syscom_sync` | `_cron_update_syscom_products` | 1 día, 03:00 | ▶️ ACTIVO (reactivado 23-jun) | Precios/stock/descontinuados. Catch-up grande la 1ª corrida. |

## Cómo verificar el estado real en prod
- Backend Odoo → Ajustes → Técnico → Automatización → Acciones planificadas (filtrar por módulo), revisar campo **Activo**.
- O por shell: `env['ir.cron'].search([]).filtered('active').mapped('name')`.
- **Regla:** si un cron está `noupdate` y desactivado en DB, el XML no lo reactiva en `-u`. Cambios de estado se hacen en DB (o con `noupdate="0"` puntual).
