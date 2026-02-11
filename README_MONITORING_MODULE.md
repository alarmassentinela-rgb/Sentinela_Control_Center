# Módulo de Monitoreo de Alarmas - Sentinela

## Descripción General
Este módulo proporciona un sistema completo de monitoreo de alarmas integrado con Odoo, similar o mejor que Securithor, pero completamente integrado con tu ERP Odoo 18.

## Características Principales
- Recepción de señales de alarma a través de API RESTful
- Dashboard en tiempo real para operadores
- Gestión de dispositivos de monitoreo
- Panel de control para clientes suscriptores
- Integración con módulo FSM para respuesta a alarmas
- Sistema de notificaciones automático
- Informes y estadísticas detalladas
- Mapas integrados para ubicación de alarmas
- Botones de pánico virtuales

## Componentes del Módulo
- `sentinela.monitoring.device`: Gestión de dispositivos de monitoreo
- `sentinela.alarm.signal`: Recepción y gestión de señales de alarma
- `sentinela.alarm.event`: Eventos de alarma con seguimiento completo
- `sentinela.response.team`: Equipos de respuesta para incidentes

## API Endpoint
- Endpoint: `/api/alarm/signals`
- Método: POST
- Autenticación: Token Bearer
- Parámetros requeridos: `device_id`, `signal_type`

## Integración con FSM
- Campo adicional en órdenes de servicio para relacionar con eventos de alarma
- Acción para crear órdenes de emergencia desde eventos de alarma
- Notificaciones push para técnicos en caso de alarmas

## Requisitos
- Odoo 18
- Módulos: sentinela_subscriptions, sentinela_fsm
- PostgreSQL (base de datos)

## Instalación
Siga las instrucciones detalladas en installation_guide.txt