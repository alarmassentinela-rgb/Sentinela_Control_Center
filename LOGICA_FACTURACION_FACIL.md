# Lógica de Facturación y Suspensión Sentinela

Este archivo explica de forma sencilla cómo el sistema gestiona los cobros y los cortes de servicio.

## 1. El Robot Centinela (Automatización)
Odoo tiene un robot interno que trabaja mientras todos duermen. Su trabajo es revisar los contratos (Suscripciones) uno por uno.

## 2. Los Pasos del Robot

### Paso A: Avisar antes de cobrar
*   **Cuándo:** 5 días antes de que se termine tu mes pagado.
*   **Acción:** Crea un "papel de preventa" (Cotización). Es como decir: *"Oye, en 5 días te voy a mandar tu factura real"*.

### Paso B: Crear la factura
*   **Cuándo:** El día exacto que te toca pagar.
*   **Acción:** Crea la factura legal. Si el cliente tiene su tarjeta guardada o paga rápido, el servicio sigue normal.

### Paso C: El Corte (Suspensión)
*   **Cuándo:** Si la factura se queda sin pagar después de la fecha límite.
*   **Acción:** El robot cambia el semáforo de tu contrato a **Rojo (Suspendido)**.
*   **Efecto:** El sistema le manda una señal a la antena de internet o al panel de alarma para que dejen de funcionar.

### Paso D: El Regreso (Reactivación)
*   **Cuándo:** En el segundo exacto en que el cliente paga.
*   **Acción:** El robot ve que ya no hay deuda, pone el semáforo en **Verde (Activo)** y le ordena a la antena o alarma que se encienda de nuevo.

## 3. Reglas de Oro
1.  **No pagas = No hay servicio:** El robot es automático, no tiene sentimientos.
2.  **Pagas = Servicio al instante:** No necesitas que un humano te reconecte, el sistema lo hace solo.
3.  **Fechas limpias:** Cada vez que pagas, el robot anota que tu próximo pago es en 30 días exactamente.
