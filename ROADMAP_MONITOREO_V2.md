# ROADMAP: MÓDULO CENTRAL DE MONITOREO "SENTINELA ELITE"

Este documento establece los objetivos técnicos y funcionales para la evolución del sistema de monitoreo Sentinela, integrando estándares internacionales de seguridad.

---

## 🎯 OBJETIVOS DE DESARROLLO

### 1. Dashboard de Alta Densidad (Grid View) ✅
*   **Estructura:** Cambiar la vista actual de tarjetas por una tabla de un solo renglón por evento. ✅
*   **Columnas:** ✅
    *   ID Registro (Consecutivo interno).
    *   N° de Cuenta (Referencia de monitoreo).
    *   Nombre de la Cuenta (Nombre comercial o de cliente).
    *   Timestamp (Fecha y hora exacta de activación).
    *   Zona/Partición (Identificador del sensor).
    *   Código de Alarma (Descripción del evento).
*   **Priorización Visual:** Coloreado de la fila completa según el nivel de urgencia (Rojo = Crítico, Naranja = Importante, Gris = Informativo). ✅
*   **Alertas Sonoras:** Reproducción de sirenas diferenciadas por prioridad. El sistema debe permitir configurar qué códigos activan sonido. ✅

### 2. Centro de Comando de Eventos (Interacción Operador) ✅
*   **Acceso:** Apertura mediante doble click sobre el evento en el dashboard. ✅
*   **Información Consolidada:** ✅
    *   Dirección física con enlace a mapas.
    *   Teléfonos directos del sitio.
    *   Directorio de contactos de emergencia del cliente.
    *   Números de emergencia local (Seguridad Pública, Bomberos, etc.).
*   **Bitácora de Operación:** Campo de texto obligatorio para registrar acciones. ✅

### 3. Integración de Patrullaje y Campo (FSM) ✅
*   **Despacho Automatizado:** Botón para convertir el evento en una "Orden de Patrullaje" enviada al móvil del guardia más cercano. ✅
*   **App de Patrullero:** ✅
    *   Ruta optimizada hacia el lugar del evento.
    *   Detalle de la zona activada (ej. "Zona 1 - Puerta Principal") para inspección dirigida.
    *   Captura obligatoria de evidencia (Fotos/Video) desde la App de Odoo.
*   **Cierre de Reporte:** El reporte del patrullero se adjunta al evento. El operador debe validar la evidencia antes de autorizar el envío del reporte final al cliente. ✅

### 4. Mantenimiento y Ciclo de Vida del Equipo ✅
*   **Orden Técnica:** Opción de generar un ticket de servicio técnico si el operador identifica fallas recurrentes o sabotaje en el equipo del cliente. ✅

---

## 🌎 BENCHMARKING: SENTINELA VS. LÍDERES MUNDIALES

| Característica | Securithor / Manitou | Sentinela Elite (Propuesta) |
| :--- | :--- | :--- |
| **Arquitectura** | Cliente-Servidor (Local) | Cloud Native (Web/Odoo) |
| **Flujo de Patrulla** | Manual o vía App externa | Integrado 100% en el ERP |
| **Evidencia** | Difícil de documentar | Multimedia (Fotos/Video) en tiempo real |
| **Reportes** | Post-evento (Días después) | Instantáneo tras validación de operador |

## 🚀 PROPUESTAS DE MEJORA (IA & AUTOMATIZACIÓN)
1.  **AI Video Verification:** Posibilidad de vincular cámaras para que el operador vea el video del momento exacto del disparo.
2.  **Omnicanalidad:** Notificación automática por WhatsApp al cliente cuando el operador inicia la atención.
3.  **SLA Tracking:** Cronómetro visual en el dashboard que muestra cuánto tiempo lleva un evento sin ser atendido (KPI de Central).

---
**Guía de Implementación:** Este documento se seguirá paso a paso. No se avanzará al siguiente punto sin la verificación funcional del anterior.
