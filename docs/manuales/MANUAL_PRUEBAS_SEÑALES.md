# Manual Técnico: Pruebas de Señales de Alarma (Emulador DT42)

**Herramienta:** Emulador DT42 (Python)
**Propósito:** Simular el comportamiento de un panel de alarma o receptora MCDI para probar el flujo de eventos en Sentinela sin hardware físico.

## 1. Arquitectura de Prueba

| Componente | Ubicación | Script | Función |
| :--- | :--- | :--- | :--- |
| **Receptor (Server)** | 192.168.3.2 | `receiver.py` | Escucha en puerto 10001, parsea Contact ID e inyecta a Odoo. |
| **Emulador (Cliente)** | PC Local | `dt42_emulator.py` | Genera tramas TCP simuladas y las envía al servidor. |

## 2. Configuración de Pruebas

### Paso 1: Activar el Servidor (Listener)
En el servidor, el receptor debe estar activo:
```bash
ssh -p 2222 egarza@192.168.3.2 "python3 /home/egarza/receiver.py"
```
*Salida esperada:* `[*] RECEPTOR SENTINELA escuchando en puerto 10001...`

### Paso 2: Ejecutar el Emulador
En la PC local:
```bash
python3 dt42_emulator.py
```

## 3. Guía de Uso del Emulador
El menú interactivo permite:

1.  **Definir Objetivo:** Confirmar IP `192.168.3.2` y Puerto `10001`.
2.  **Cambiar Cuenta (Opción 'A'):** Es vital usar un número de cuenta que **ya exista en Odoo** (creado vía importación o manualmente) para ver el evento asociado al cliente correcto.
3.  **Enviar Señales:**
    *   `1` = Robo (Burglary)
    *   `2` = Fuego
    *   `3` = Pánico
    *   `M` = Manual (Para probar códigos específicos como `401` Apertura / `402` Cierre).

## 4. Verificación de Éxito
*   **Éxito Técnico:** El emulador muestra `✅ ACK Recibido`.
*   **Éxito Funcional:** En Odoo (Modelo `sentinela.alarm.signal` o `monitoring.device`), debe aparecer el registro de la señal con la fecha y hora exacta.
