# Manual de Operación: Central de Monitoreo Sentinela

**Versión:** 1.0 (05/02/2026)
**Módulo:** sentinela_monitoring

## 1. Arquitectura del Sistema
El sistema de monitoreo se compone de tres piezas clave que trabajan en sincronía:

1.  **Receptor (Script Python):** Un programa invisible que corre en el servidor, escuchando el puerto 10001. Recibe las señales de los paneles de alarma, las traduce y las inyecta en Odoo.
2.  **Odoo (Backend):** La base de datos central que almacena clientes, dispositivos, señales y eventos.
3.  **Dashboard en Vivo (Frontend):** La pantalla que ve el operador para reaccionar a las emergencias en tiempo real.

## 2. Flujo de una Alarma
1.  El panel de alarma (o emulador) envía una trama Contact ID al puerto 10001.
2.  El Receptor recibe la trama, confirma con un `ACK` y busca el dispositivo en Odoo.
3.  **Si el dispositivo existe:** Crea la señal y genera un **Evento de Alarma**.
4.  **Si NO existe:** Crea un dispositivo temporal "Auto-Created" y genera una alerta de prioridad alta.
5.  El Dashboard en Vivo se actualiza (o notifica) mostrando la nueva línea.
6.  El operador hace clic en **"ATENDER"** para gestionar la incidencia.

## 3. Guía de Solución de Problemas (Troubleshooting)

### A. El Receptor aparece "OFF" en el Dashboard
*   **Causa:** El script `receiver.py` se detuvo o el servidor se reinició.
*   **Solución:** Contactar a soporte técnico para reiniciar el servicio en el backend (`nohup python3 receiver.py ...`).

### B. Error "View types not defined tree" al entrar a Dispositivos
*   **Causa:** Conflicto de versión en Odoo 18.
*   **Solución Rápida:**
    1.  Activar modo desarrollador.
    2.  Ir a Ajustes > Técnico > Acciones de Ventana.
    3.  Buscar "Dispositivos de Monitoreo".
    4.  Cambiar `view_mode` de `tree,form` a `list,form`.

### C. Importación de Clientes fallida
*   Usar el script `scripts/import_alarm_subscriptions.py`.
*   Revisar el archivo `errores_importacion.csv` generado para ver qué líneas fallaron.
*   Asegurarse de que el usuario `api_user` tenga permisos de administración.

## 4. Credenciales de Sistema (API)
Para scripts externos o integraciones:
*   **URL:** `http://192.168.3.2:8070`
*   **DB:** `Sentinela_V18`
*   **User:** `api_user`
*   **Password:** `admin`
