# Actualización Integral del Sistema Sentinela v2026.02.13 (Parte 2)
**Estado:** Automatización Logística y Fiscal completada.
**Módulos Afectados:** `sentinela_syscom`, `sentinela_cfdi_prodigia`, `sentinela_subscriptions`.

---

## 🛒 1. Integración Comercial con Syscom (Nivel Experto)

Transformamos Odoo en un cerebro logístico conectado a Syscom en tiempo real.

### A. Automatización de Compras (Dropshipping & Stock)
*   **Nuevo Botón "Enviar a Syscom":** Envia los productos de la Orden de Compra directamente al carrito de Syscom.
*   **Inteligencia Dropshipping:**
    *   Si la venta es para un cliente final (Tienda Web o Pedido Especial), Odoo envía la **dirección del cliente** a Syscom automáticamente.
    *   Activa alertas para recordar el uso de "Envío de Cortesía" (Marca Blanca).
*   **Gestión Multi-Sucursal:** Soporte para pedidos que Syscom divide en múltiples envíos. Odoo rastrea cada paquete por separado.

### B. Rastreo Logístico 24/7
*   **Robot de Rastreo:** Un cron job revisa cada hora el estado de tus pedidos.
*   **Alertas de Llegada:** Cuando una guía cambia a **"Entregado"**, Odoo:
    1.  Publica un aviso urgente en la Orden de Compra.
    2.  Genera una tarea automática para el Almacenista ("Recibir Mercancía").

### C. Estrategia de Precios (Tienda Web)
Se crearon tarifas dinámicas que se ajustan solas si Syscom cambia sus costos:
1.  **Tarifa B2C (Público):** Costo + 35%.
2.  **Tarifa B2B (Instaladores):** Costo + 15%.

---

## ⚖️ 2. Inteligencia Fiscal (CFDI 4.0 Automatizado)

Se eliminó el error humano en la elección de métodos de pago.

### A. Detección PPD vs PUE
*   **PPD Automático:** Si la factura tiene plazos de pago (crédito), el sistema fuerza **MetodoPago="PPD"** y **FormaPago="99"**.
*   **PUE Automático:** Si es contado, permite elegir la forma de pago real o usa "01 Efectivo" por defecto.

### B. Blindaje de Remisiones
*   Se configuró el sistema para impedir que documentos marcados como **"Remisión / Nota de Venta"** sean timbrados ante el SAT, protegiendo tus folios fiscales.

---

## 🔄 3. El "Modo Sentinela Full" (Auto-Facturación)

Automatización total del ciclo de ingresos recurrentes.

*   **Interruptor "Auto-Facturar":** Nuevo control en el contrato.
*   **Flujo Automático:**
    1.  Genera la Venta.
    2.  Confirma la Venta.
    3.  Crea la Factura/Remisión.
    4.  Valida y Publica el documento.
*   **Resultado:** El día 1 de cada mes, tus facturas están listas para cobro sin un solo clic humano.

---

## 📋 Resumen Técnico para Soporte
*   **Cron Jobs Nuevos:** `_cron_sync_syscom_logistics` (Cada hora).
*   **Campos Clave:** `syscom_shipment_ids` (PO), `auto_bill` (Suscripción), `invoice_fiscal_type` (Account Move).
*   **Validaciones:** Bloqueo de timbrado para tipo 'remision' en `account_move.py`.

**Documento generado por:** Orquestador IA Sentinela.
