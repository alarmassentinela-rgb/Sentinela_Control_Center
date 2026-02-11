# DellCli Control Center

**Host Local:** DellCli (WSL/Windows)
**Usuario:** dell / egarza
**Fecha Actual:** 15 de Enero, 2026

Este índice centraliza el control de operaciones locales y la conexión con el servidor principal (MasAdmin/Sentinela).

---

## 📂 Estructura Local (`/mnt/c/Users/dell/DellCli/`)

### 🛠️ Scripts de Diagnóstico y Red
Scripts Python para gestión de red Mikrotik y diagnósticos.
- `audit_mikrotik.py` - Auditoría de configuraciones.
- `check_ports.py` - Verificación de puertos abiertos.
- `diagnose_connection.py` - Diagnóstico de conectividad.
- `fix_bridge.py` / `fix_internet.py` - Reparaciones automáticas de red.
- `configure_mikrotik.py` - Configuración de router.
- `setup_suspension.py` / `check_suspension_status.py` - Gestión de suspensión de servicios.

### 📦 Paquetería Sentinela (Versiones)
Archivos comprimidos del proyecto principal.
- `sentinela_final_vXX.tar.gz` - Historial de versiones (v5 a v24).
- `sentinela_subscriptions_v3.tar.gz` - Módulo de suscripciones.

### 🧩 Módulos Odoo Locales
Código fuente de módulos en desarrollo/mantenimiento.
- **`sentinela_subscriptions/`**: Gestión de suscripciones recurrentes, perfiles Mikrotik y gráficas de tráfico.
- **`sentinela_syscom/`**: Integración y sincronización con Syscom (Productos, Categorías).

### 📄 Documentación y Sesiones
- **`/docs/manuales/`**: Guías técnicas y procedimientos.
    - [Conexión SSH MasAdmin](docs/manuales/conexion_ssh_masadmin.md)
- **`/sessions/`**: Bitácora diaria de trabajo y memoria del proyecto.
    - [2026-01-15 - Comodato Locks & Smart Renewal](sessions/2026-01-15_dell.md)
    - [2026-01-17 - Leasing, Stripe Payments & Reconnection](sessions/2026-01-17_dell.md)
    - [2026-01-19 - FSM Module, Transfers & Grouped Billing](sessions/2026-01-19_dell.md)
    - [2026-01-19 PM - FSM Auto-Dispatch & Final Data Prep](sessions/2026-01-19_dell_pm.md)
    - [2026-01-20 - FSM Portal Fixes & Usability](sessions/2026-01-20_dell.md)
    - [2026-01-20 - FSM Customer Portal & Sales Integration](sessions/2026-01-20_dell.md)

---

## ☁️ Servidor Remoto: MasAdmin (Sentinela)

**IP:** `192.168.3.2` | **Puerto SSH:** `2222` | **Usuario:** `egarza`

El servidor aloja los servicios productivos y herramientas de automatización.

### Servicios Activos
| Servicio | Puerto | Estado | Descripción |
|----------|--------|--------|-------------|
| **Odoo 17** | `8069` | ✅ Online | ERP Principal (Ruta: `/opt/odoo/odoo17`) |
| **n8n** | `5678` | ✅ Online | Automatización de flujos (Docker) |
| **PostgreSQL**| `5432` | ✅ Online | Base de datos |

### Estructura Remota Clave (`~/`)
- **`AiCli/`**: Directorio de gestión CLI remoto (Scripts, Logs, Config).
- **`n8n-docker/`**: Configuración de contenedores de automatización.
- **`odoo18-migration/`**: Archivos de migración.
- **`nginx-configs/`**: Configuraciones de proxy inverso.

---

## 🚀 Accesos Rápidos

### Comandos de Conexión
```bash
# Conectar al servidor (usando la configuración corregida)
ssh -p 2222 -i /tmp/ssh_keys/id_ed25519 egarza@192.168.3.2
```

### Comandos de Mantenimiento Local
```bash
# Verificar manuales
ls -R docs/manuales

# Listar sesiones recientes
ls -lt sessions/ | head
```