# DellCli Control Center

**Host Local:** DellCli (WSL/Windows) | **Servidor:** AleaSystems (192.168.3.2)
**Estado:** ✅ Sistema Pulido y Seguro (Día 17 Ready)

---

## 📂 Estructura Local (`/mnt/c/Users/dell/DellCli/`)
**Estado Git:** ✅ Sincronizado (GitHub: [Sentinela_Control_Center](https://github.com/alarmassentinela-rgb/Sentinela_Control_Center))

### 🛠️ Herramientas de Cobranza y Monitoreo
- **`Motor de Cobranza`**: Lógica flexible de periodos y días de gracia en Odoo 18.
- **`Centro de Comando`**: Dashboard OWL v3.5 con audio global y radar de deudas.
- **`Receptor V6`**: Identificación inteligente de dueños de cuenta.

### 🧩 Módulos Odoo Maestro
- **`sentinela_subscriptions/`**: Cobranza, candados de seguridad y motivos de cancelación.
- **`sentinela_monitoring/`**: Dashboard en vivo, señales TCP y alertas omnipresentes.

### 📄 Documentación y Sesiones
- **`LOGICA_FACTURACION_FACIL.md`**: Guía del Motor de Cobranza para Irma.
- **`/sessions/`**:
    *   [2026-02-11 - Orquestación y Persistencia Inicial](sessions/2026-02-11_final_orchestration.md)
    *   [2026-02-12 - Refinamiento, Seguridad e Inventarios](sessions/2026-02-12_final_polish.md)
    *   [2026-02-17 - Expansión GPS y Blindaje AleaSystems](sessions/2026-02-17_server_expansion.md)
    *   [2026-02-17 - Inteligencia de Patrullaje y Cierre de Ciclo](sessions/2026-02-17_patrol_intelligence.md)
    *   [2026-02-20 - Integración Maestra Securithor y Capa de Monitoreo](sessions/2026-02-20_securithor_integration.md)
    *   [2026-02-18 - Autodescubrimiento Syscom y Colas Asíncronas](sessions/2026-02-18_syscom_robot_discovery.md)

---

## ☁️ Servidor Remoto: AleaSystems (Sentinela)

**IP:** `192.168.3.2` | **Puerto SSH:** `2222` | **Usuario:** `egarza`
*(Nota: Puertos 22 y 8069 están desactivados)*

### Servicios Activos
| Servicio | Puerto | Estado | Descripción |
|----------|--------|--------|-------------|
| **Odoo 18** | `8070` | ✅ Online | ERP Principal (Comand Center) |
| **Traccar** | `8082` | ✅ Online | Plataforma GPS Profesional |
| **Proxy Manager**| `81` | ✅ Online | Admin de Dominios y SSL |
| **Receptor** | `10001`| ✅ Online | Escucha de señales Contact ID |
| **PostgreSQL**| `5432` | ✅ Online | Base de datos V18 |

---

## 🚀 Accesos Rápidos

### Comandos de Orquestación
```bash
# Iniciar Proyecto Sentinela (Mañana)
# "Inicia Proyecto Sentinela: Lee project_summary.md y el último log en sessions/, conéctate al servidor y dime qué sigue."

# Comando Dashboard Local
# dashboard
```
