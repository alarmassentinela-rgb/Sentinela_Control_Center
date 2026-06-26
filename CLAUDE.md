# DellCli — repo de trabajo Sentinela

Directorio de trabajo de Enrique Garza (WSL/Windows). **NO es un addons-path en sí ni el árbol del server** — es el origen desde el que se sincroniza código a producción. Contiene los addons de Odoo de Sentinela, varias apps standalone, y mucho material suelto (scripts, backups, docs de sesión).

> Cada subproyecto importante tiene su propio `CLAUDE.md` con el detalle (modelos, crones, trampas). Este archivo raíz solo **orienta**: qué es cada cosa y cómo se despliega. Si agregas un módulo/proyecto, añádelo a la tabla.

## Regla de oro del deploy (aplica a TODO)
El server `192.168.3.2` **NO es un git working tree**. Editar local no cambia nada en prod hasta hacer `rsync`. Saltar el rsync = el `docker exec -u` actualiza con **código viejo**.

- **Módulos Odoo:** skill `release-modulo` (bump versión + commit + tag + push) → skill `deploy-modulo` (rsync local→server → `-u` en STAGING `Sentinela_STAGING` → `-u` en prod `V18` → verificar).
- **Apps standalone (netwatch, receiver, golfbookvip, senticar):** NO usan esas skills. Es rsync + `docker compose restart` / `systemctl` según el caso (ver el CLAUDE.md/README de cada una).
- **Odoo:** 18 Community. DB prod = `V18`, DB lab = `Sentinela_STAGING` (contenedor `odoo-lab`, navegador `http://192.168.3.2:8075`, sin crones).

## Módulos Odoo (`sentinela_*` con `__manifest__.py`)
| Módulo | Versión | App | Doc | Rol |
|---|---|---|---|---|
| `sentinela_subscriptions` | 18.0.1.3.86 | ✅ | [CLAUDE.md](sentinela_subscriptions/CLAUDE.md) | **Corazón.** Facturación recurrente + provisioning (internet/alarma/GPS). Reemplaza MASadmin/Argus. |
| `sentinela_monitoring` | 18.0.1.7.0 | ✅ | [CLAUDE.md](sentinela_monitoring/CLAUDE.md) | Central de monitoreo de alarmas. Reemplaza Securithor. |
| `sentinela_fsm` | 18.0.1.5.1 | ✅ | [CLAUDE.md](sentinela_fsm/CLAUDE.md) | Gestión de Servicios (órdenes de campo: install/repair/maint/patrol). |
| `sentinela_syscom` | 18.0.1.3.0 | ✅ | [CLAUDE.md](sentinela_syscom/CLAUDE.md) | Integración catálogo/proveedor Syscom. |
| `sentinela_cfdi_prodigia` | 18.0.1.1.14 | dep | [CLAUDE.md](sentinela_cfdi_prodigia/CLAUDE.md) | Timbrado CFDI 4.0 vía Prodigia + diseño factura/remisión. Dependencia de subscriptions. |
| `sentinela_digital_sign` | 18.0.1.0.0 | dep | [CLAUDE.md](sentinela_digital_sign/CLAUDE.md) | Firma de PDF desde el portal del cliente. Dependencia de subscriptions. |
| `sentinela_api` | 18.0.0.1.0 | dep | [CLAUDE.md](sentinela_api/CLAUDE.md) | **Portal COC.** Capa REST/JSON que expone los `sentinela_*` al portal web y app móvil. No duplica lógica. Esqueleto (Sprint 0). |

## Apps standalone (NO son módulos Odoo)
| Proyecto | Stack | Dónde / dominio | Doc |
|---|---|---|---|
| `sentinela_netwatch` | Flask + gunicorn + Docker + TimescaleDB | "Vigilante WISP": ping a antenas, dashboard NOC `:8090`, Telegram. Deploy = rsync + `docker compose restart`. | [CLAUDE.md](sentinela_netwatch/CLAUDE.md) |
| `sentinela_receiver` | Python + systemd | Receptor TCP de señales de alarma (alimenta `sentinela_monitoring`). Reemplaza la familia `receiver_v*.py` legacy. | `sentinela_receiver/README.md` |
| `sentinela_chatwoot_bot` | FastAPI + Docker | AgentBot de Chatwoot (inbox "Reportes Sentinela"): convierte WhatsApp entrante en orden FSM (Odoo XML-RPC) + handoff a soporte. Server `/opt/sentinela_chatwoot_bot`, red `chatwoot_default`. Deploy = rsync + `docker compose up -d --build`. | [CLAUDE.md](sentinela_chatwoot_bot/CLAUDE.md) |
| `sentinela_coc` | FastAPI gateway + Next.js SPA + Docker | **Portal Centro de Operaciones del Cliente (COC).** Gateway BFF (`api.sentinela.mx`) + SPA (`portal.sentinela.mx`); consume el addon `sentinela_api`. Deploy = rsync + `docker compose`. STAGING primero. | [README](sentinela_coc/README.md) |
| `proyecto golfbookvip` | FastAPI + PostgreSQL + Redis | **golfbookvip.com** — reservas/torneos de golf. En server `/opt/golfbookvip`. ⚠️ deploy frontend: `.next` bind-mount → `docker cp` tras build. | `proyecto golfbookvip/README.md` |
| `proyecto aleasystem` | Next.js 15 | Sitio corporativo AleaSystem.io. Deploy Docker puerto 8300. | — |
| **SentiCar** (no hay carpeta de fuente en el repo) | Traccar branded | **radar.senticar.com** (GPS, Traccar en `192.168.3.2:8082` LAN, expuesto vía Cloudflare Tunnel). Fuente de la app Android en `~/senticar-app`; los scripts `*_senticar_*.py` de la raíz administran el sitio/portal. | — |

## Sobre el desorden de la raíz
La raíz mezcla código con material operativo suelto: `*.tar.gz` (respaldos versionados, **gitignored**), scripts de un solo uso (`audit_*.py`, `rebuild_senticar_*.py`, `setup_*_portal.py`), docs de sesión (`RESUMEN_SESION_*.md`, `AUDITORIA_*.md`), CSVs, PDFs de contratos. No asumas que un archivo suelto está vivo — confirma antes de usarlo. `.gitignore` excluye: `__pycache__/`, `.env`, `*.log`, `*.tar.gz`, `.ssh/`, credenciales VPN, `vpn_laptop/`.

## Estado / memoria
El **estado vivo** del proyecto (decisiones, fechas, freezes, incidentes) NO va en estos CLAUDE.md — vive en la memoria persistente (`MEMORY.md` y archivos `project_*`/`session_*`/`reference_*`). Los CLAUDE.md documentan el **cómo es el código**; la memoria, el **qué está pasando**.
