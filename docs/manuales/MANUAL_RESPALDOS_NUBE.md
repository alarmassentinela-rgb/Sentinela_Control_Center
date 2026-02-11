# Manual de Infraestructura: Respaldos en la Nube (Google Drive)

**Fecha de Implementación:** 02/02/2026
**Tecnología:** Rclone + Script Bash + Cron
**Servidor:** 192.168.3.2

## 1. Arquitectura de Respaldo
Se ha configurado un sistema automatizado que extrae la base de datos y los módulos de Odoo, los empaqueta y los sube a una unidad de Google Drive externa para garantizar la continuidad del negocio ante fallos físicos del servidor.

### Componentes:
*   **Herramienta de Sincronización:** `rclone` (v1.73.0)
*   **Destino Remoto:** Google Drive (Configurado como `gdrive:Sentinela_Backups`)
*   **Script de Ejecución:** `/home/egarza/scripts/backup_to_gdrive.sh`

## 2. Funcionamiento del Script
El script realiza los siguientes pasos secuenciales:
1.  **Dump de Base de Datos:** Extrae la BD `Sentinela_V18` desde el contenedor Docker `odoo18-migration-db-1`.
2.  **Empaquetado de Addons:** Comprime la carpeta `/home/egarza/odoo18-migration/addons`.
3.  **Compresión Final:** Genera un archivo `.tar.gz` con el formato `sentinela_full_AAAAMMDD_HHMMSS.tar.gz`.
4.  **Subida:** Transfiere el archivo a la nube mediante `rclone copy`.
5.  **Limpieza:** Borra los archivos temporales del servidor local.

## 3. Automatización (Cron)
El respaldo se ejecuta automáticamente todos los días a las **3:00 AM**.

**Verificación de Tarea Programada:**
```bash
crontab -l
# Salida esperada:
# 0 3 * * * /home/egarza/scripts/backup_to_gdrive.sh >> /tmp/backup_log.txt 2>&1
```

## 4. Comandos Útiles

**Ejecución Manual (Bajo Demanda):**
```bash
ssh -p 2222 egarza@192.168.3.2 "/home/egarza/scripts/backup_to_gdrive.sh"
```

**Verificar archivos en la Nube:**
```bash
ssh -p 2222 egarza@192.168.3.2 "rclone lsd gdrive:Sentinela_Backups"
```

**Restauración de Emergencia:**
1.  Descargar el archivo desde Drive a `/tmp`.
2.  Descomprimir.
3.  Restaurar BD: `cat db_dump.sql | docker exec -i odoo18-migration-db-1 psql -U odoo Sentinela_V18`
