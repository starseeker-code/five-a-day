# ============================================================================
# MAKEFILE - Comandos útiles para Five a Day
# ============================================================================
# Simplifica comandos comunes de Docker y Django

.PHONY: help build up down restart logs shell migrate makemigrations test clean backup restore

# ============================================================================
# HELP
# ============================================================================
help:
	@echo "╔════════════════════════════════════════════════════════════╗"
	@echo "║           FIVE A DAY - Docker Commands                    ║"
	@echo "╚════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Inicio:"
	@echo "  make setup          - Configuración inicial (copia .env)"
	@echo "  make build          - Construir las imágenes Docker"
	@echo "  make up             - Iniciar todos los servicios"
	@echo "  make down           - Detener todos los servicios"
	@echo "  make restart        - Reiniciar todos los servicios"
	@echo ""
	@echo "📊 Monitoreo:"
	@echo "  make logs           - Ver logs de todos los servicios"
	@echo "  make logs-web       - Ver logs del servicio web"
	@echo "  make logs-db        - Ver logs de PostgreSQL"
	@echo "  make ps             - Ver estado de los servicios"
	@echo "  make stats          - Ver uso de recursos"
	@echo ""
	@echo "🛠️  Django:"
	@echo "  make shell          - Abrir shell de Django"
	@echo "  make bash           - Abrir bash en el contenedor web"
	@echo "  make migrate        - Aplicar migraciones"
	@echo "  make makemigrations - Crear nuevas migraciones"
	@echo "  make createsuperuser- Crear superusuario"
	@echo "  make collectstatic  - Recolectar archivos estáticos"
	@echo ""
	@echo "🗄️  Base de Datos:"
	@echo "  make dbshell        - Abrir PostgreSQL shell"
	@echo "  make backup         - Hacer backup de la BD"
	@echo "  make restore FILE=  - Restaurar backup (uso: make restore FILE=backup.sql)"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  make test           - Ejecutar tests"
	@echo "  make test-coverage  - Tests con coverage"
	@echo ""
	@echo "🧹 Limpieza:"
	@echo "  make clean          - Limpiar contenedores y volúmenes"
	@echo "  make clean-all      - Limpiar todo (¡cuidado! pierdes datos)"
	@echo ""

# ============================================================================
# SETUP
# ============================================================================
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ Archivo .env creado. Por favor, edítalo con tus configuraciones."; \
	else \
		echo "⚠️  El archivo .env ya existe."; \
	fi

# ============================================================================
# DOCKER COMPOSE
# ============================================================================
build:
	@echo "🔨 Construyendo imágenes..."
	docker compose build

up:
	@echo "🚀 Iniciando servicios..."
	docker compose up -d
	@echo "✅ Servicios iniciados!"
	@echo "📱 Aplicación: http://localhost:8000"
	@echo "🔧 Admin: http://localhost:8000/admin"

down:
	@echo "🛑 Deteniendo servicios..."
	docker compose down
	@echo "✅ Servicios detenidos!"

restart:
	@echo "🔄 Reiniciando servicios..."
	docker compose restart
	@echo "✅ Servicios reiniciados!"

# ============================================================================
# LOGS & MONITORING
# ============================================================================
logs:
	docker compose logs -f

logs-web:
	docker compose logs -f web

logs-db:
	docker compose logs -f db

ps:
	docker compose ps

stats:
	docker stats

# ============================================================================
# DJANGO COMMANDS
# ============================================================================
shell:
	@echo "🐍 Abriendo Django shell..."
	docker compose exec web python project/manage.py shell

bash:
	@echo "💻 Abriendo bash en contenedor web..."
	docker compose exec web bash

migrate:
	@echo "📦 Aplicando migraciones..."
	docker compose exec web python project/manage.py migrate

makemigrations:
	@echo "📝 Creando migraciones..."
	docker compose exec web python project/manage.py makemigrations

createsuperuser:
	@echo "👤 Creando superusuario..."
	docker compose exec web python project/manage.py createsuperuser

collectstatic:
	@echo "📁 Recolectando archivos estáticos..."
	docker compose exec web python project/manage.py collectstatic --noinput

# ============================================================================
# DATABASE
# ============================================================================
dbshell:
	@echo "🗄️  Abriendo PostgreSQL shell..."
	docker compose exec db psql -U fiveaday_user -d fiveaday_db

backup:
	@echo "💾 Creando backup de base de datos..."
	@mkdir -p backups
	docker compose exec db pg_dump -U fiveaday_user fiveaday_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✅ Backup creado en backups/"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "❌ Error: Debes especificar FILE=ruta/al/backup.sql"; \
		exit 1; \
	fi
	@echo "♻️  Restaurando backup desde $(FILE)..."
	docker compose exec -T db psql -U fiveaday_user -d fiveaday_db < $(FILE)
	@echo "✅ Backup restaurado!"

# ============================================================================
# TESTING
# ============================================================================
test:
	@echo "🧪 Ejecutando tests..."
	docker compose exec web python project/manage.py test

test-coverage:
	@echo "🧪 Ejecutando tests con coverage..."
	docker compose exec web pytest --cov=core --cov-report=html

# ============================================================================
# CLEANUP
# ============================================================================
clean:
	@echo "🧹 Limpiando contenedores detenidos y volúmenes no utilizados..."
	docker compose down
	docker system prune -f
	@echo "✅ Limpieza completada!"

clean-all:
	@echo "⚠️  ¡CUIDADO! Esto eliminará TODOS los datos."
	@read -p "¿Estás seguro? (escribe 'yes'): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v; \
		docker system prune -af --volumes; \
		echo "✅ Todo limpio (datos borrados)"; \
	else \
		echo "❌ Operación cancelada"; \
	fi

# ============================================================================
# DEVELOPMENT
# ============================================================================
dev:
	@echo "🔧 Iniciando modo desarrollo..."
	docker compose up

dev-build:
	@echo "🔧 Construyendo e iniciando modo desarrollo..."
	docker compose up --build

# ============================================================================
# PRODUCTION
# ============================================================================
prod-build:
	@echo "🚀 Construyendo para producción..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml build

prod-up:
	@echo "🚀 Iniciando en modo producción..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# ============================================================================
# UTILITY
# ============================================================================
install-deps:
	@echo "📦 Instalando dependencias..."
	docker compose exec web poetry install

update-deps:
	@echo "🔄 Actualizando dependencias..."
	docker compose exec web poetry update
