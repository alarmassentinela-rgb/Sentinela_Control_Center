#!/bin/bash
echo "Iniciando Sentinela Dashboard Web..."
# Matar procesos previos en el puerto 8080 si existen
fuser -k 8080/tcp 2>/dev/null
python3 ComandCenter/dashboard_web.py
