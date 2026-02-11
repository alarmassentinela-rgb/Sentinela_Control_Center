# Manual de Operaciones: Importación de Suscripciones de Alarma

**Objetivo:** Migrar masivamente clientes de monitoreo desde MasAdmin hacia Odoo (Sentinela), asegurando la creación de contratos y la vinculación técnica de paneles.

## 1. Archivos Necesarios
*   **Plantilla CSV:** `plantilla_importacion_alarmas.csv`
*   **Script Python:** `scripts/import_alarm_subscriptions.py`

## 2. Preparación de Datos (Excel/CSV)
La plantilla debe llenarse respetando estrictamente las columnas.

**Campo Crítico: `account_number`**
Es OBLIGATORIO incluir el número de cuenta del panel (Ej: `9001`, `A100`).
*   Si este campo está vacío, solo se creará el contrato administrativo.
*   Si tiene datos, el script creará automáticamente el **Dispositivo de Monitoreo** y lo vinculará.

**Ejemplo de Fila:**
```csv
partner_id,product_id,price_unit,start_date,service_type,account_number,state
"Juan Perez","Monitoreo Residencial",500.00,2024-01-01,alarm,9001,active
```

## 3. Ejecución de la Importación
Desde la terminal local (donde están los archivos):

```bash
python3 scripts/import_alarm_subscriptions.py
```

El script imprimirá en pantalla el ID de la suscripción y del dispositivo creado por cada línea.

## 4. Lógica de Negocio en Odoo (Backend)
Se ha modificado el modelo `sentinela.subscription` para controlar el ciclo de vida del monitoreo:

### A. Vinculación
*   Modelo: `sentinela.subscription`
*   Nuevo Campo: `monitoring_device_ids` (One2many -> `sentinela.monitoring.device`)

### B. Automatización de Estados
1.  **Activar Contrato:** Al poner la suscripción en "Activo", el sistema busca los dispositivos vinculados y cambia su estado a `active`.
2.  **Suspender (Falta de Pago):** Al ejecutar "Suspender Servicio", los dispositivos vinculados pasan a `inactive`.
3.  **Cancelar:** Desactiva permanentemente los dispositivos.

**Importancia:** Esto asegura que el área de monitoreo sepa en tiempo real si un cliente está al corriente de pagos o suspendido, sin necesidad de consultar administración.
