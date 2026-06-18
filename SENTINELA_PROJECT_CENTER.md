# Proyecto Sentinela: Master Context Document
**Última Actualización:** 18 de Junio, 2026
**Estado:** Operación en producción (Odoo 18). Migración MASadmin/Argus/Securithor → módulos Sentinela en curso; facturación recurrente activa.

## 1. Visión General
Sentinela es un ecosistema integral basado en Odoo 18 que orquesta servicios de seguridad, conectividad y energía. El sistema integra la administración comercial (suscripciones/facturación) con la operación técnica en tiempo real (monitoreo de alarmas/gestión de red).

---

## 2. Líneas de Negocio (Multiservicio)
El sistema está diseñado para manejar flujos lógicos distintos según el tipo de suscripción:

| Servicio | Componente Técnico Principal | Acción de Automatización |
| :--- | :--- | :--- |
| **Monitoreo de Alarmas** | Central de Monitoreo (OWL Dashboard) | Creación de Eventos desde Señales Contact-ID |
| **Internet (WISP)** | Integración MikroTik (API) | Gestión de PPPoE, Perfiles y Suspensión |
| **Senticar (GPS)** | Plataforma propia Traccar (`radar.senticar.com`) + Suscripciones GPS | Vinculación de IMEI/Unidades, comandos SMS, links de rastreo |
| **Field Service (FSM)** | App Móvil / Órdenes de Servicio | Instalaciones, Cámaras, Energía Solar, Mantenimiento |
| **Seguridad Electrónica** | Control de Acceso / CCTV | Gestión de proyectos e inventario |

---

## 3. Arquitectura del Módulo de Monitoreo
La Central de Monitoreo es el corazón táctico del proyecto:

### A. El Receptor (Backend)
- **Script:** `receiver_v6.py` (y versiones posteriores).
- **Función:** Escucha tramas Contact-ID, valida números de cuenta y las inyecta en Odoo vía XML-RPC/JSON-RPC.
- **Persistencia:** Gestionado por `systemd` y monitoreado en sesión `tmux` (monitor1).

### B. El Dashboard (Frontend OWL)
Interfaz de alta densidad para operadores con 3 pestañas críticas:
1.  **Alarmas:** Eventos en estado `active`. Disparan alertas sonoras inteligentes.
2.  **Tráfico en Vivo:** Historial de señales crudas (`sentinela.alarm.signal`) recibidas por el receptor.
3.  **Eventos Pendientes:** Gestión de alarmas en proceso (`in_progress`), pausadas o escaladas.

---

## 4. Lógica de Suscripciones y Contratos
- **Contratos Digitales:** Generación de PDF automáticos con firmas electrónicas integradas.
- **Gestión de Equipos:** Diferenciación entre equipos en Comodato (empresa), Propiedad del Cliente o Leasing.
- **Ciclo de Facturación:** Automatización de cobros mensuales, bimestrales, etc., con suspensión técnica automática en Mikrotik/Monitoreo ante falta de pago.

---

## 5. Infraestructura y Entorno de Trabajo
- **Ruta Oficial:** `/mnt/c/Users/dell/DellCli` (Sincronizado vía OneDrive para persistencia local/laptop).
- **Servidor Local:** 192.168.3.2 (AleaSystems)
    *   **SSH:** Puerto `2222`, Usuario `egarza`.
    *   **Acceso WSL:** Requiere habilitar el rango `172.19.0.0/16` en UFW y verificar Fail2Ban.
    *   **Odoo PROD:** Puerto `8070` → DB `Sentinela_V18` (Port 8069 legacy desactivado).
    *   **Odoo STAGING/LAB:** Puerto `8075` → DB `Sentinela_STAGING` (contenedor `odoo-lab`, sin crons). ⚠️ STAGING SIEMPRE por `:8075`, nunca `:8070` (pegar STAGING a `:8070` tiró los crons de prod el 12-jun).
    *   **n8n:** Puerto `5678`.
- **Despliegue:** el server NO es git working tree. Editar local → `rsync` → `docker exec -u` (skills `release-modulo` + `deploy-modulo`). Sin rsync, el `-u` corre código viejo.
- **Respaldo:** Repositorio GitHub `Sentinela_Control_Center`.

---

## 6. Reglas de Oro para el Agente (Contexto Permanente)
1.  **No mezclar servicios:** El "Tráfico de Internet" (Mikrotik) es distinto al "Tráfico de Señales" (Alarmas).
2.  **Seguridad:** Nunca exponer credenciales de Mikrotik o API Keys en logs o commits.
3.  **UI/UX:** El dashboard debe ser de "Alta Densidad" (mucha información, poco espacio desperdiciado) siguiendo el estilo de centrales profesionales como Securithor.

---

## 7. Módulos y versiones (al 18-jun-2026)
> La versión vive en cada `__manifest__.py`; esta tabla es referencia rápida y puede quedar atrás. El **detalle vivo** de cada módulo está en su `CLAUDE.md`.

| Módulo | Versión | Rol |
|---|---|---|
| `sentinela_subscriptions` | 18.0.1.4.0 | Corazón: facturación recurrente + provisioning (internet/alarma/GPS). |
| `sentinela_monitoring` | 18.0.1.29.1 | Central de monitoreo de alarmas (reemplaza Securithor). |
| `sentinela_fsm` | 18.0.1.8.9 | Gestión de Servicios (órdenes de campo + patrullaje). |
| `sentinela_syscom` | 18.0.1.4.0 | Integración catálogo/proveedor Syscom. |
| `sentinela_cfdi_prodigia` | 18.0.1.1.15 | Timbrado CFDI 4.0 vía Prodigia. |
| `sentinela_digital_sign` | 18.0.1.0.0 | Firma de PDF desde el portal del cliente. |

**Dónde vive el estado actual (esto NO):** este documento es la visión a alto nivel.
El detalle al día está en (1) el `CLAUDE.md` de cada módulo, (2) la memoria persistente
del agente (`MEMORY.md` + archivos `project_*`/`reference_*`), y (3) el historial de git.
