# Manual Técnico: Conexión SSH al Servidor Odoo (MasAdmin)

**Fecha de Creación:** 15 de Enero, 2026
**Servidor Objetivo:** MasAdmin (Odoo)
**Dirección IP:** 192.168.3.2
**Puerto SSH:** 2222
**Usuario:** egarza

## 1. Descripción
Este documento detalla el procedimiento para establecer una conexión segura SSH con el servidor de desarrollo Odoo. Incluye la solución específica para problemas de permisos de llaves en entornos WSL/Windows.

## 2. Prerrequisitos
- **Llave Privada:** Ubicada localmente en `.ssh/id_ed25519` (o equivalente).
- **Llave Pública:** La parte pública (`.ssh/id_ed25519.pub`) debe estar agregada en el archivo `~/.ssh/authorized_keys` del servidor remoto.

## 3. Problema Común: Permisos de Archivos en WSL
Al trabajar en WSL (Windows Subsystem for Linux) montado sobre el sistema de archivos de Windows (`/mnt/c/...`), el comando `chmod` a veces no puede establecer los permisos estrictos (600) requeridos por SSH. Esto resulta en el error:
```
WARNING: UNPROTECTED PRIVATE KEY FILE!
Permissions 0777 for '...' are too open.
```

## 4. Solución y Procedimiento de Conexión

### Paso 1: Copiar la llave a un entorno nativo de Linux
Para garantizar los permisos correctos, copiamos la llave privada a un directorio temporal nativo de Linux (ej. `/tmp`).

```bash
mkdir -p /tmp/ssh_keys
cp .ssh/id_ed25519 /tmp/ssh_keys/
```

### Paso 2: Ajustar Permisos
Aplicamos los permisos de lectura/escritura solo para el propietario.

```bash
chmod 600 /tmp/ssh_keys/id_ed25519
```

### Paso 3: Conexión
Ejecutamos el comando SSH apuntando a la llave con los permisos corregidos.

```bash
ssh -p 2222 -i /tmp/ssh_keys/id_ed25519 egarza@192.168.3.2
```

## 5. Verificación
Una vez conectado, puede verificar su identidad y el host con:
```bash
whoami
hostname
# Debería retornar: egarza / masadmin
```

## 6. Historial de Cambios
- **15/01/2026:** Documentación inicial creada tras resolver conflicto de permisos "UNPROTECTED PRIVATE KEY FILE" moviendo las llaves a `/tmp`.
