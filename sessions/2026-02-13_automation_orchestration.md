# Informe de Mejoras Técnicas: Orquestación Sentinela v2026.02.13
**Estado:** Implementado y listo para pruebas de campo.
**Módulos Afectados:** `sentinela_subscriptions`, `sentinela_fsm`, `sentinela_syscom`.

---

## 🚀 1. Automatización: Flujo de Venta a Instalación
Se eliminó la brecha operativa entre el cierre de una venta y el inicio de la instalación técnica.
*   **Gatillo:** Al confirmar una `SaleOrder` que contiene productos de suscripción.
*   **Acción:** 
    1.  Crea automáticamente el **Contrato de Suscripción** en estado `draft`.
    2.  Crea la **Orden de Servicio (FSM)** de tipo 'Instalación'.
    3.  Vincula ambos registros para trazabilidad total.
*   **Beneficio:** Asegura que cada venta sea asignada a un técnico inmediatamente.

## 🛠️ 2. Sincronización Inteligente de Datos Técnicos
El técnico es ahora el principal validador de la base de datos desde el campo.
*   **Validación de Series:** Se añadió el campo `lot_id` a los materiales de FSM. El técnico selecciona el número de serie físico usado.
*   **Inyección Automática:** Al finalizar la orden (`action_finish`), el sistema inyecta en el Contrato:
    *   Número de Serie/IMEI oficial.
    *   Coordenadas GPS reales de instalación (Lat/Lon).
    *   ICCID de la SIM.
    *   Configuraciones específicas (Zonas de alarma, MAC de antena, etc.).

## 📅 3. Motor de Mantenimiento Preventivo
Implementación de un ciclo de vida proactivo para la retención de clientes.
*   **Lógica de Frecuencia:** El contrato permite definir visitas cada 3, 6 o 12 meses.
*   **Cron de Generación:** Un robot diario revisa las fechas de `Próximo Mantenimiento` y crea los tickets de servicio automáticamente.
*   **Auto-Reset:** Cualquier visita técnica exitosa actualiza la `Fecha de Último Mantenimiento`, reprogramando el ciclo de forma dinámica.

## 🛑 4. Sincronización de Estado y Cierre Técnico
Protección de la integridad de la base de datos activa.
*   **Tipo de Servicio 'Removal':** Nueva categoría para retiro de equipos.
*   **Cierre Automático:** Al finalizar una orden de retiro, el contrato vinculado pasa a estado `closed` y su estado técnico a `cut` sin intervención administrativa.
*   **Auditoría:** Se registra el motivo del cierre automáticamente en el chatter del contrato.

## 🖼️ 5. Expediente Digital Centralizado
Centralización de la evidencia física para soporte y facturación.
*   **Galería de Evidencias:** Nueva pestaña en el Contrato que extrae todas las fotos de todas las órdenes de servicio relacionadas.
*   **Vista Kanban:** Interfaz visual que permite ver miniaturas de "Antes", "Durante" y "Después" directamente en el expediente del cliente.
*   **Beneficio:** Facilita la resolución de disputas y la auditoría de calidad de instalaciones.

---

## 📋 Próximos Pasos Recomendados
1.  **Capacitación de Técnicos:** Instruir en el uso de la selección de Lote/Serie en la App móvil.
2.  **Validación de Inventarios:** Monitorear el descuento automático de stock configurado en `action_finish`.
3.  **Monitoreo de Cron:** Verificar la primera corrida del cron de mantenimiento preventivo mañana a las 00:00 hrs.

**Documento generado por:** Orquestador IA Sentinela.
