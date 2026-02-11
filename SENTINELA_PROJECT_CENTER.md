# Proyecto Sentinela: Master Context Document
**Última Actualización:** 11 de Febrero, 2026
**Estado:** Fase de Estabilización y Refinamiento de UI/UX (Odoo 18)

## 1. Visión General
Sentinela es un ecosistema integral basado en Odoo 18 que orquesta servicios de seguridad, conectividad y energía. El sistema integra la administración comercial (suscripciones/facturación) con la operación técnica en tiempo real (monitoreo de alarmas/gestión de red).

---

## 2. Líneas de Negocio (Multiservicio)
El sistema está diseñado para manejar flujos lógicos distintos según el tipo de suscripción:

| Servicio | Componente Técnico Principal | Acción de Automatización |
| :--- | :--- | :--- |
| **Monitoreo de Alarmas** | Central de Monitoreo (OWL Dashboard) | Creación de Eventos desde Señales Contact-ID |
| **Internet (WISP)** | Integración MikroTik (API) | Gestión de PPPoE, Perfiles y Suspensión |
| **Rastreo GPS** | Módulo de Suscripciones GPS | Vinculación de IMEI y Unidades |
| **Field Service (FSM)** | App Móvil / Órdenes de Servicio | Instalaciones, Cámaras, Energía Solar, Mantenimiento |
| **Seguridad Electrónica** | Control de Acceso / CCTV | Gestión de proyectos e inventario |

---

## 3. Arquitectura del Módulo de Monitoreo
La Central de Monitoreo es el corazón táctico del proyecto:

### A. El Receptor (Backend)
- **Script:** `receiver_v6.py` (y versiones posteriores).
- **Función:** Escucha tramas Contact-ID, valida números de cuenta y las inyecta en Odoo vía XML-RPC/JSON-RPC.
- **Persistencia:** Gestionado por `systemd` y monitoreado en sesión `tmux` (monitor1).

### B. El Dashboard (Frontend OWL)
Interfaz de alta densidad para operadores con 3 pestañas críticas:
1.  **Alarmas:** Eventos en estado `active`. Disparan alertas sonoras inteligentes.
2.  **Tráfico en Vivo:** Historial de señales crudas (`sentinela.alarm.signal`) recibidas por el receptor.
3.  **Eventos Pendientes:** Gestión de alarmas en proceso (`in_progress`), pausadas o escaladas.

---

## 4. Lógica de Suscripciones y Contratos
- **Contratos Digitales:** Generación de PDF automáticos con firmas electrónicas integradas.
- **Gestión de Equipos:** Diferenciación entre equipos en Comodato (empresa), Propiedad del Cliente o Leasing.
- **Ciclo de Facturación:** Automatización de cobros mensuales, bimestrales, etc., con suspensión técnica automática en Mikrotik/Monitoreo ante falta de pago.

---

## 5. Infraestructura y Entorno de Trabajo
- **Ruta Oficial:** `/mnt/c/Users/dell/DellCli` (Sincronizado vía OneDrive para persistencia local/laptop).
- **Servidor Local:** 192.168.3.2 (n8n, Evolution API, Odoo).
- **Respaldo:** Repositorio GitHub `Sentinela_Control_Center`.

---

## 6. Reglas de Oro para el Agente (Contexto Permanente)
1.  **No mezclar servicios:** El "Tráfico de Internet" (Mikrotik) es distinto al "Tráfico de Señales" (Alarmas).
2.  **Seguridad:** Nunca exponer credenciales de Mikrotik o API Keys en logs o commits.
3.  **UI/UX:** El dashboard debe ser de "Alta Densidad" (mucha información, poco espacio desperdiciado) siguiendo el estilo de centrales profesionales como Securithor.
