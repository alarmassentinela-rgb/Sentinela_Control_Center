# Notas de Despliegue - Sentinela Command Center
**Fecha:** 11 de Febrero de 2026
**Ubicación del Proyecto:** `/mnt/c/Users/dell/DellCli/ComandCenter`

## Resumen del Trabajo
Se ha implementado un Dashboard de monitoreo local unificado que mapea:
1. **Estado de Red (Mikrotik):** Conexión vía API (socket raw) para contar sesiones PPPoE activas.
2. **Estado de Alarmas (Receiver):** Monitoreo del log `receiver_new.log` para detectar señales recientes y estado de salud del servicio (Active/Stale).

## Componentes Creados
- `dashboard_web.py`: Servidor web ligero (Zero-Dependency) que corre en el puerto **8080**.
- `dashboard.py`: Versión de terminal (CLI) para monitoreo rápido.
- `dashboard_start.sh`: Script de arranque automático que limpia procesos previos en el puerto 8080.

## Configuración de Red Local
- **Host:** `0.0.0.0` (Escucha en todas las interfaces).
- **Puerto:** `8080`
- **URLs de acceso local:**
    - http://localhost:8080
    - http://127.0.0.1:8080
    - http://172.19.68.211:8080 (IP de la interfaz WSL)

## Notas Técnicas
- El entorno no cuenta con `flask` ni `routeros_api` instalados globalmente, por lo que se utilizó una implementación de **Socket puro** para Mikrotik y **http.server** para el Dashboard Web.
- El log de alarmas se considera "STALE" si no hay actividad en los últimos 10 minutos.

---
*Documentación generada por el Orquestador Sentinela.*
