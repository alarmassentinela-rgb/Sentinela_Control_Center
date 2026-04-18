# 🏌️ GolfBookVIP.com

Plataforma completa de golf: scoring en tiempo real, hándicap WHS automático,
gestión de clubes, grupos, apuestas y feed social.

## 🛠️ Stack
- **Backend:** Python 3.11 + FastAPI
- **Base de datos:** PostgreSQL 16
- **Cache / WebSockets:** Redis 7
- **Proxy:** Nginx
- **SSL:** Let's Encrypt (Certbot)
- **Contenedores:** Docker + Docker Compose

---

## 🚀 Instalación en Servidor

### 1. Requisitos previos
```bash
# Instalar Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo apt install docker-compose-plugin

# Instalar Make
sudo apt install make
```

### 2. Clonar el proyecto
```bash
git clone https://github.com/tuusuario/golfbookvip.git
cd golfbookvip
```

### 3. Configurar variables de entorno
```bash
cp .env.example .env
nano .env   # Editar con tus valores reales
```

### 4. Generar SECRET_KEY segura
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 5. Primer deploy
```bash
# Construir imágenes
make build

# Levantar servicios (sin SSL primero)
make up

# Correr migraciones
make migrate
```

### 6. Configurar SSL
```bash
# Obtener certificado
make ssl-init

# Reiniciar nginx con SSL
make restart
```

---

## 📋 Comandos Útiles

```bash
make up              # Levantar todos los servicios
make down            # Detener servicios
make logs            # Ver logs en tiempo real
make logs-api        # Ver logs de la API
make migrate         # Correr migraciones
make backup          # Backup de la base de datos
make shell           # Entrar al contenedor de la API
make db-shell        # Entrar a PostgreSQL
make deploy          # Deploy completo
make status          # Ver estado de contenedores
```

---

## 🌐 URLs

| Servicio | URL |
|---|---|
| API REST | https://api.golfbookvip.com/api/v1 |
| WebSocket | wss://api.golfbookvip.com/ws/ |
| Documentación | https://api.golfbookvip.com/docs |
| Frontend PWA | https://golfbookvip.com |
| Portainer | http://tu-servidor:9000 |

---

## 📁 Estructura del Proyecto

```
golfbookvip/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── dependencies.py
│   ├── models/
│   ├── schemas/
│   ├── routers/
│   ├── services/
│   └── websockets/
├── alembic/
├── nginx/
│   ├── nginx.conf
│   └── conf.d/
├── postgres/
│   └── init.sql
├── certbot/
├── tests/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── Makefile
├── .env.example
└── .gitignore
```

---

## 🔒 Seguridad

- Nunca subas `.env` a git
- Cambia todas las contraseñas del `.env.example`
- Usa contraseñas de mínimo 32 caracteres para DB y Redis
- El puerto de PostgreSQL NO está expuesto al exterior
- Nginx tiene rate limiting configurado

---

## 📦 Backups Automáticos

Agrega esto al crontab del servidor para backups diarios:

```bash
crontab -e

# Backup diario a las 3am
0 3 * * * cd /ruta/golfbookvip && make backup
```

---

## 🧑‍💻 Desarrollo Local

```bash
# Levantar solo DB y Redis
docker compose up -d db redis

# Correr API localmente
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
