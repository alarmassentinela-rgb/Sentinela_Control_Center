# Manual Técnico y Mapa de Proyecto - Sentinela Monitoreo
**Última Actualización:** 06 de Febrero, 2026 - 17:40 CST
**Estado General:** Sistema Operativo, Receptor en Línea, Dashboard 2.0 funcional.

---

## 🗺️ Mapa de Arquitectura (Contexto)

El ecosistema Sentinela se divide en 4 componentes clave que ya están comunicados:

1.  **Receptor de Alarmas (`receiver.py`):**
    *   **Ubicación:** Servidor Remoto (`192.168.3.2`) en `/home/egarza/`.
    *   **Función:** Escucha tramas Contact ID en puerto `10001`.
    *   **Conector:** Habla con Odoo vía XML-RPC (`port 8070`).
    *   **Estado:** ONLINE (Auto-latido cada 10s).

2.  **Núcleo Odoo (Servidor `192.168.3.2`):**
    *   **Base de Datos:** `Sentinela_V18`.
    *   **Modelos Clave:** 
        *   `sentinela.subscription`: Gestiona contratos y ahora el campo `monitoring_account_number`.
        *   `res.partner`: Direcciones de servicio separadas de las fiscales.
        *   `sentinela.alarm.event`: Tickets de alarma creados por el receptor.

3.  **Dashboard de Monitoreo (OWL JS):**
    *   **Ubicación:** Menú "Dashboard en Vivo" en Odoo.
    *   **Características:** Semáforo de prioridades, tiempos de respuesta en vivo, integración con Google Maps mini-iframes.

4.  **Base de Datos Externa (Excel):**
    *   **Archivo:** `cuentas060226.xlsx` -> Procesado a `cuentas_extraidas.xlsx` (264 cuentas).

---

## 🛠️ Intervenciones Realizadas (06/02/2026)

### A. Estructura de Datos y Base de Datos
*   **Nuevo Campo:** Se agregó `monitoring_account_number` a `sentinela.subscription`.
*   **Fix de DB:** Se creó manualmente la columna en PostgreSQL para evitar errores de carga.
*   **Separación Fiscal:** Implementación de lógica para crear "Contactos Hijos" para direcciones de servicio, evitando que se mezclen datos de la central con datos de facturación.

### B. Dashboard "Securithor Killer"
*   **UI/UX:** Reemplazo de tablas por tarjetas de evento dinámicas.
*   **Lógica de Tiempo:** Implementación de contadores relativos (ej. "Hace 2 min").
*   **Mapas:** Renderizado condicional de mapas GPS para cada evento.
*   **Audio:** Sistema de alerta sonora activado para eventos críticos.

### C. Estabilización del Receptor
*   **Versión Final:** `v6` desplegada como `receiver.py` en el servidor remoto.
*   **Corrección de Prioridades:** Eliminación de errores por campos de texto; ahora usa IDs reales de Odoo.
*   **Heartbeat Estricto:** Latidos cada 10s con tolerancia de 30s para detección inmediata de caídas.

---

## 📋 Pendientes para Mañana (Hoja de Ruta)

1.  **Reanudar Importación Masiva:**
    *   El script `execute_account_update_v4_final.py` procesó los primeros registros pero se detuvo por inestabilidad de red.
    *   **Meta:** Completar las 260 cuentas restantes.
    *   **Recomendación:** Correrlo en lotes de 20 en 20 para evitar saturar el servidor.

2.  **Habilitar One2many de Dispositivos:**
    *   Comentamos temporalmente la línea `monitoring_device_ids` en `subscription.py` para resolver una dependencia circular.
    *   **Acción:** Descomentar y actualizar cuando el sistema esté 100% estable.

3.  **Pruebas de Campo:**
    *   Simular alarmas con el emulador DT42 desde diferentes cuentas para verificar que el Dashboard asigne el mapa y el nombre del negocio correctamente.

---

## 📂 Archivos Críticos en este Directorio (`DellCli`)
*   `receiver_v6.py`: Código fuente maestro del receptor.
*   `cuentas_extraidas.xlsx`: Datos listos para cargar.
*   `execute_account_update_v4_final.py`: Script para terminar la carga mañana.
*   `INFORME_INTERVENCION_06FEB2026.md`: Este reporte.

**Servidor Remoto:** `192.168.3.2`
**Odoo Web:** `http://192.168.3.2:8070`
