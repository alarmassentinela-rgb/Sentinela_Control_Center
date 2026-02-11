# 🤖 Motor de Cobranza Profesional Sentinela (Odoo 18)

Este archivo describe la lógica avanzada de facturación, periodos y suspensión automatizada implementada el 11 de febrero de 2026. El sistema ha pasado de una regla fija a un motor totalmente configurable por cada cliente.

---

## 📅 1. El Concepto de "Periodo Vivo"
A diferencia de sistemas rígidos, Sentinela ahora maneja periodos explícitos:
*   **Inicio del Periodo:** Fecha exacta en que el cliente empieza a consumir el mes (ej. 17 de enero).
*   **Fin del Periodo:** Fecha exacta en que termina su derecho de uso (ej. 16 de febrero).
*   **Visibilidad:** Estos campos son visibles en el contrato, permitiendo al operador ajustar meses específicos si es necesario.

---

## ⚙️ 2. El Cerebro Configurable (Lead Times)
Cada contrato tiene ahora 3 "perillas" de control para el robot:

### A. Anticipación de Factura (`invoice_gen_type`)
*   **Rango:** 0 a 30 días antes del inicio del periodo.
*   **Función:** Define cuándo el robot despierta para enviar el aviso de cobro.
*   **Caso de uso:** A clientes morosos se les puede facturar 15 días antes; a clientes premium, el mismo día.

### B. Fecha Límite de Pago (`payment_due_type`)
*   **Rango:** 0 a 15 días **después** del fin del periodo.
*   **Función:** Define el vencimiento legal. 
*   **Lógica de Crédito:** Permite dar servicio "fiado" (el cliente consume el mes y tiene X días para pagar al terminar).

### C. Días de Gracia para Corte (`service_cut_type`)
*   **Rango:** 0 a 15 días después del vencimiento.
*   **Función:** Es el "colchón" antes de apagar el equipo.
*   **Efecto:** Si vence el plazo y no hay pago, el robot ejecuta la suspensión automática en MikroTik/Alarma.

---

## 🤖 3. Automatización (El Cron Inteligente)

### Flujo de Facturación
El sistema escanea a diario:
1. Calcula la `Fecha de Generación` = `Inicio del Periodo` - `Días de Anticipación`.
2. Si hoy es esa fecha, crea la Cotización/Factura.
3. **Agrupación Inteligente (Caso Miriam):** Si un cliente tiene varios contratos que coinciden en su fecha de generación, el robot los une en una sola factura global.

### Flujo de Suspensión
1. El robot revisa la `Fecha de Corte` calculada.
2. Si hoy es posterior a esa fecha y la factura sigue pendiente:
   *   Manda comando `disable` al MikroTik.
   *   Inactiva el dispositivo en la Central de Monitoreo.
3. Al detectar el pago, se ejecuta el comando `enable` de forma instantánea (Reactivación en milisegundos).

---

## 🏆 Reglas de Oro del Nuevo Motor
1.  **Flexibilidad Total:** El sistema se adapta al cliente, no el cliente al sistema.
2.  **Cero Intervención Humana:** El corte y la reactivación son 100% automáticos.
3.  **Transparencia:** El cliente recibe avisos claros basados en su periodo real de uso.
