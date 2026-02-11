# Informe Técnico: Sistema de Monitoreo Sentinela (Odoo 18)
**Fecha Última Actualización:** 05 de Febrero, 2026
**Proyecto:** Migración y Refinamiento del Ecosistema Sentinela

---

## 1. Resumen de Intervención (05/02/2026)
Se completó la implementación del **Centro de Comando de Monitoreo** con un ciclo completo funcional: desde la recepción de señales TCP hasta el dashboard visual del operador. Se resolvieron múltiples desafíos de compatibilidad con Odoo 18 y permisos de usuario.

## 2. Componentes Implementados

### A. Receptor Universal (V6)
- **Tecnología:** Python con XML-RPC nativo de Odoo.
- **Funciones:**
    - Escucha en puerto 10001 (Estándar Contact ID).
    - Autenticación robusta con usuario dedicado (`api_user`).
    - **Auto-Provisioning:** Crea dispositivos automáticamente si recibe una señal de una cuenta desconocida.
    - **Generación de Tickets:** Crea automáticamente un `Alarm Event` en estado "Activo" para cada señal crítica.
    - **Heartbeat:** Se reporta cada minuto a Odoo para indicar que está "Online".

### B. Dashboard en Vivo (Centro de Comando)
- **Tecnología:** Odoo OWL (JavaScript + XML).
- **Características:**
    - Vista de tabla moderna con colores por prioridad.
    - Indicador de estatus del receptor (ON/OFF).
    - Botón de acción rápida "ATENDER".
    - Actualización automática ante nuevas notificaciones.

### C. Importación Masiva de Clientes
- Script optimizado `import_alarm_subscriptions.py`.
- Logro: 224 clientes importados y vinculados correctamente.
- Manejo de errores: Generación automática de archivo CSV con los registros fallidos para reintento.

## 3. Resolución de Incidencias Críticas

### Error: `View types not defined tree found in act_window action 589`
- **Causa:** Incompatibilidad de Odoo 18 con la definición de vistas antigua.
- **Solución:** Corrección manual y por script en la base de datos (`UPDATE ir_act_window SET view_mode = 'list,form'`).

### Error: `Fault 4: Access Denied`
- **Causa:** El usuario API no tenía permisos para crear contactos.
- **Solución:** Se otorgaron permisos de `base.group_system` y `base.group_partner_manager` al usuario `api_user`.

---

## Estado de Módulos Actualizado
| Módulo | Estado | Función Principal |
| :--- | :--- | :--- |
| **sentinela_monitoring** | **Producción** | Recepción, Dashboard y Gestión de Eventos. |
| **Receptor (Script)** | **Activo** | Corriendo en background (PID persistente). |
| **Dashboard** | **Activo** | Disponible en menú "Dashboard en Vivo". |

---

## 4. Intervención: Estabilización y Persistencia (10/02/2026)

### A. Reparación del Dashboard (Odoo 18)
- **Problema:** Error de carga al entrar a "Central de Monitoreo" debido a funciones de tiempo (`isOverdue`, `getRelativeTime`) no definidas en el JS pero invocadas en el XML.
- **Solución:** Se implementaron las funciones utilizando la librería **Luxon** integrada en Odoo 18. Se ajustó la plantilla OWL para usar el contexto `this.` y se sincronizaron los archivos para eliminar versiones de "mantenimiento".

### B. Infraestructura de Alta Disponibilidad
- **Tmux:** Se configuró la sesión `monitor1` para permitir el monitoreo interactivo del receptor sin riesgo de interrupción.
- **Autostart (Systemd):** Se creó el servicio `sentinela-receptor.service` que garantiza que el receptor se inicie automáticamente tras un reinicio del servidor o corte de energía.
- **Rutas:** Se estandarizó el uso de `/home/egarza/receiver_v6.py` como la versión productiva oficial.

### C. Importación de Datos
- **Estatus:** Finalizada al 100%. Todas las cuentas de clientes han sido migradas y vinculadas a sus respectivas suscripciones de monitoreo.

---
**Próxima Fase:**
- Desarrollo de la App Móvil para patrulleros (FSM).
- Configuración de envío de correos automáticos a clientes.
- Integración con mapas GPS para rutas de patrullaje.
