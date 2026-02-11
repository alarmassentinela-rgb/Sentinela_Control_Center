# Diagrama de Estructura del Proyecto

```mermaid
graph TD
    subgraph Local_DellCli ["💻 Local: DellCli (WSL/Windows)"]
        direction TB
        
        subgraph Scripts ["🛠️ Scripts & Tools"]
            Net[Network/Mikrotik Scripts]
            Diag[Diagnostics]
        end
        
        subgraph Packages ["📦 Paquetería"]
            V_Hist[Sentinela Versions .tar.gz]
            Sub_Pkg[Subscriptions Module]
        end
        
        subgraph Modules ["Ez Odoo Modules"]
            Sub_Mod[sentinela_subscriptions]
            Sys_Mod[sentinela_syscom]
        end
        
        subgraph Documentation ["📄 Docs & Logs"]
            Manuals[docs/manuales/*.md]
            Sessions[sessions/*.md]
            Index[index.md]
        end
    end

    subgraph Remote_MasAdmin ["☁️ Remoto: MasAdmin (192.168.3.2)"]
        direction TB
        
        subgraph Services ["🚀 Servicios Activos"]
            Odoo[Odoo 17 :8069]
            n8n[n8n (Docker) :5678]
            PG[PostgreSQL :5432]
        end
        
        subgraph Remote_Dirs ["ww Directorios Clave (~/)"]
            AiCli[AiCli/ (CLI Management)]
            N8n_Docker[n8n-docker/]
            Odoo_Mig[odoo18-migration/]
            Nginx[nginx-configs/]
            Opt_Odoo[/opt/odoo/odoo17]
        end
    end

    %% Connections
    Local_DellCli ==>|SSH -p 2222 (Key: id_ed25519)| Remote_MasAdmin
    Modules -.->|Deploy/Sync| Opt_Odoo
    Scripts -.->|Manage/Audit| Remote_MasAdmin

    classDef local fill:#e1f5fe,stroke:#01579b,stroke-width:2px;
    classDef remote fill:#f3e5f5,stroke:#4a148c,stroke-width:2px;
    classDef service fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px;
    
    class Local_DellCli local;
    class Remote_MasAdmin remote;
    class Odoo,n8n,PG service;
```
