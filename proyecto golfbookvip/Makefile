# ============================================================
# GOLFBOOKVIP.COM — Makefile
# Comandos útiles para administrar el proyecto
# ============================================================

.PHONY: help build up down restart logs shell db-shell migrate backup

# Colores
GREEN  = \033[0;32m
YELLOW = \033[0;33m
RESET  = \033[0m

help: ## Mostrar ayuda
	@echo "$(GREEN)GolfBookVIP — Comandos disponibles:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(RESET) %s\n", $$1, $$2}'

# ── Docker ───────────────────────────────────────────────
build: ## Construir imágenes
	docker compose build --no-cache

up: ## Levantar todos los servicios
	docker compose up -d
	@echo "$(GREEN)✅ golfbookvip corriendo en https://api.golfbookvip.com$(RESET)"

down: ## Detener todos los servicios
	docker compose down

restart: ## Reiniciar servicios
	docker compose restart

restart-api: ## Reiniciar solo la API
	docker compose restart api

logs: ## Ver logs en tiempo real
	docker compose logs -f

logs-api: ## Ver logs de la API
	docker compose logs -f api

logs-db: ## Ver logs de PostgreSQL
	docker compose logs -f db

status: ## Ver estado de los contenedores
	docker compose ps

# ── Base de Datos ─────────────────────────────────────────
migrate: ## Correr migraciones
	docker compose run --rm migrate

migrate-create: ## Crear nueva migración (uso: make migrate-create name=add_table)
	docker compose exec api alembic revision --autogenerate -m "$(name)"

db-shell: ## Acceder a PostgreSQL
	docker compose exec db psql -U golfuser -d golfbookvip

# ── API Shell ─────────────────────────────────────────────
shell: ## Acceder al contenedor de la API
	docker compose exec api bash

# ── SSL ───────────────────────────────────────────────────
ssl-init: ## Obtener certificado SSL por primera vez
	docker compose run --rm certbot certonly \
		--webroot --webroot-path=/var/www/certbot \
		--email admin@golfbookvip.com \
		--agree-tos --no-eff-email \
		-d golfbookvip.com -d www.golfbookvip.com -d api.golfbookvip.com

ssl-renew: ## Renovar certificado SSL
	docker compose run --rm certbot renew

# ── Backups ───────────────────────────────────────────────
backup: ## Backup de la base de datos
	@mkdir -p ./backups
	docker compose exec db pg_dump -U golfuser golfbookvip | \
		gzip > ./backups/golfbookvip_$(shell date +%Y%m%d_%H%M%S).sql.gz
	@echo "$(GREEN)✅ Backup guardado en ./backups/$(RESET)"

restore: ## Restaurar backup (uso: make restore file=backups/golfbookvip_xxx.sql.gz)
	gunzip -c $(file) | docker compose exec -T db psql -U golfuser -d golfbookvip

# ── Producción ────────────────────────────────────────────
deploy: ## Deploy completo (build + migrate + up)
	@echo "$(YELLOW)🚀 Iniciando deploy de golfbookvip...$(RESET)"
	git pull origin main
	docker compose build
	docker compose run --rm migrate
	docker compose up -d
	@echo "$(GREEN)✅ Deploy completado$(RESET)"

# ── Limpieza ──────────────────────────────────────────────
clean: ## Limpiar contenedores e imágenes no usadas
	docker system prune -f
	docker volume prune -f
