# ============================================================================
# MAKEFILE — Five a Day eVolution
# ============================================================================
# Docker and Django shortcuts. Run `make` or `make help` for usage.

.PHONY: help setup build up down restart stop start rebuild dev logs logs-web \
        logs-db ps stats shell bash migrate makemigrations createsuperuser \
        collectstatic check dbshell backup restore reset-db test test-local \
        test-verbose test-coverage test-models test-services test-views \
        clean clean-all health url send-test-email generate-payments

# ============================================================================
# HELP
# ============================================================================
help:
	@echo ""
	@echo "  Five a Day — Make Commands"
	@echo "  =========================="
	@echo ""
	@echo "  Setup & Build:"
	@echo "    make setup            Copy .env.example to .env"
	@echo "    make build            Build Docker images"
	@echo "    make rebuild          Full rebuild (no cache) + start"
	@echo "    make rebuild-web      Rebuild only the web image"
	@echo ""
	@echo "  Docker Lifecycle:"
	@echo "    make up               Start all services (detached)"
	@echo "    make down             Stop and remove containers"
	@echo "    make restart          Restart all services"
	@echo "    make restart-web      Restart only web"
	@echo "    make restart-db       Restart only database"
	@echo "    make stop             Stop without removing"
	@echo "    make start            Start stopped containers"
	@echo "    make dev              Start in foreground (logs visible)"
	@echo "    make dev-build        Build + start in foreground"
	@echo ""
	@echo "  Monitoring:"
	@echo "    make logs             Tail logs (all services)"
	@echo "    make logs-web         Tail web logs only"
	@echo "    make logs-db          Tail database logs only"
	@echo "    make ps               Show running services"
	@echo "    make stats            Show resource usage"
	@echo "    make health           Full health check (Django + DB)"
	@echo "    make url              Show access URLs"
	@echo ""
	@echo "  Django:"
	@echo "    make shell            Django shell inside container"
	@echo "    make bash             Bash shell inside container"
	@echo "    make migrate          Apply all migrations"
	@echo "    make makemigrations   Create migrations (all apps)"
	@echo "    make createsuperuser  Create Django superuser"
	@echo "    make collectstatic    Collect static files"
	@echo "    make check            Run Django system checks"
	@echo ""
	@echo "  Database:"
	@echo "    make dbshell          PostgreSQL interactive shell"
	@echo "    make backup           Dump DB to backups/"
	@echo "    make restore FILE=x   Restore from SQL file"
	@echo "    make reset-db         Drop and recreate DB (destructive!)"
	@echo ""
	@echo "  Testing:"
	@echo "    make test             Run all tests (Docker)"
	@echo "    make test-local       Run all tests (local, no Docker)"
	@echo "    make test-verbose     Run all tests with verbose output"
	@echo "    make test-coverage    Run tests with coverage report"
	@echo "    make test-models      Run only model tests"
	@echo "    make test-services    Run only service tests"
	@echo "    make test-views       Run only view tests"
	@echo "    make test-fast        Run tests, stop on first failure"
	@echo ""
	@echo "  Email:"
	@echo "    make send-test-email  Send a test birthday email"
	@echo "    make test-all-emails  Send one test of each email template"
	@echo ""
	@echo "  Payments:"
	@echo "    make generate-payments          Generate current month"
	@echo "    make generate-payments-dry      Preview without creating"
	@echo ""
	@echo "  Cleanup:"
	@echo "    make clean            Remove stopped containers + prune"
	@echo "    make clean-all        Remove everything including volumes"
	@echo ""

# ============================================================================
# SETUP
# ============================================================================
setup:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "Created .env — edit it with your configuration."; \
	else \
		echo ".env already exists."; \
	fi

# ============================================================================
# DOCKER COMPOSE — LIFECYCLE
# ============================================================================
build:
	docker compose build

up:
	docker compose up -d --remove-orphans
	@echo "Started: http://localhost:8000"

down:
	docker compose down

restart:
	docker compose restart

restart-web:
	docker compose restart web

restart-db:
	docker compose restart db

stop:
	docker compose stop

start:
	docker compose start

rebuild:
	docker compose down
	docker compose build --no-cache
	docker compose up -d
	@echo "Rebuilt and started: http://localhost:8000"

rebuild-web:
	docker compose stop web
	docker compose build --no-cache web
	docker compose up -d web

dev:
	docker compose up --remove-orphans

dev-build:
	docker compose up --build --remove-orphans

# ============================================================================
# MONITORING
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

health:
	@echo "=== Services ==="
	@docker compose ps
	@echo ""
	@echo "=== Django check ==="
	@docker compose exec web python project/manage.py check 2>/dev/null || echo "(web not running)"
	@echo ""
	@echo "=== PostgreSQL ==="
	@docker compose exec db pg_isready -U fiveaday_user 2>/dev/null || echo "(db not running)"
	@echo ""
	@echo "=== Health endpoint ==="
	@curl -sf http://localhost:8000/health/ 2>/dev/null || echo "(not reachable)"

url:
	@echo "App:   http://localhost:8000"
	@echo "Admin: http://localhost:8000/admin"
	@echo "Login: http://localhost:8000/login"

# ============================================================================
# DJANGO COMMANDS
# ============================================================================
shell:
	docker compose exec web python project/manage.py shell

bash:
	docker compose exec web bash

migrate:
	docker compose exec web python project/manage.py migrate

makemigrations:
	docker compose exec web python project/manage.py makemigrations students billing core comms

createsuperuser:
	docker compose exec web python project/manage.py createsuperuser

collectstatic:
	docker compose exec web python project/manage.py collectstatic --noinput

check:
	docker compose exec web python project/manage.py check

# ============================================================================
# DATABASE
# ============================================================================
dbshell:
	docker compose exec db psql -U fiveaday_user -d fiveaday_db

backup:
	@mkdir -p backups
	docker compose exec db pg_dump -U fiveaday_user fiveaday_db > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "Backup saved to backups/"

restore:
	@if [ -z "$(FILE)" ]; then \
		echo "Usage: make restore FILE=backups/backup.sql"; \
		exit 1; \
	fi
	docker compose exec -T db psql -U fiveaday_user -d fiveaday_db < $(FILE)
	@echo "Restored from $(FILE)"

reset-db:
	@echo "WARNING: This will destroy ALL data in the database."
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v; \
		docker compose up -d; \
		sleep 15; \
		echo "Database recreated."; \
		docker compose ps; \
	else \
		echo "Cancelled."; \
	fi

# ============================================================================
# TESTING
# ============================================================================
# Tests use PostgreSQL by default (requires `make up` for the DB container).
# Set TEST_DB_ENGINE=sqlite to fall back to SQLite for quick local runs.

# Run all tests inside Docker (uses the container's PostgreSQL)
test:
	docker compose exec web python -m pytest project/tests/ -v --tb=short

# Run tests locally against the Docker PostgreSQL (default)
test-local:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/ -v --tb=short

# Run tests locally with SQLite (no Docker needed)
test-sqlite:
	cd project && TEST_DB_ENGINE=sqlite python -m pytest tests/ -v --tb=short

# Verbose output with full tracebacks
test-verbose:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/ -v --tb=long -s

# Coverage report
test-coverage:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/ --cov=core --cov=students --cov=billing --cov=comms --cov-report=term-missing --cov-report=html
	@echo "HTML report: project/htmlcov/index.html"

# Run specific test modules
test-models:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/test_models.py -v --tb=short

test-services:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/test_services.py -v --tb=short

test-views:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/test_views.py -v --tb=short

# Stop on first failure
test-fast:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/ -x -v --tb=short

# Run tests matching a keyword (usage: make test-k K=payment)
test-k:
	cd project && TEST_DB_HOST=localhost python -m pytest tests/ -v -k "$(K)" --tb=short

# ============================================================================
# EMAIL & PAYMENTS
# ============================================================================
send-test-email:
	docker compose exec web python project/manage.py send_email --template happy_birthday --test

test-all-emails:
	docker compose exec web python project/manage.py test_all_emails --list

generate-payments:
	docker compose exec web python project/manage.py generate_payments

generate-payments-dry:
	docker compose exec web python project/manage.py generate_payments --dry-run

# ============================================================================
# CLEANUP
# ============================================================================
clean:
	docker compose down
	docker system prune -f

clean-all:
	@echo "WARNING: This will remove ALL containers, images, and volumes."
	@read -p "Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker compose down -v; \
		docker system prune -af --volumes; \
		echo "Everything removed."; \
	else \
		echo "Cancelled."; \
	fi

# ============================================================================
# VERSIONING
# ============================================================================
# App version is defined in two places:
#   1. pyproject.toml → version = "x.y.z"
#   2. project/settings.py → APP_VERSION fallback = "x.y.z"
# This command updates both at once.

version:
	@if [ -z "$(V)" ]; then \
		echo "Usage: make version V=1.1.0"; \
		echo ""; \
		echo "Current version:"; \
		grep 'version = ' pyproject.toml | head -1; \
		grep 'APP_VERSION' project/project/settings.py | head -1; \
		exit 1; \
	fi
	@sed -i 's/^version = ".*"/version = "$(V)"/' pyproject.toml
	@sed -i 's/APP_VERSION = os.getenv("APP_VERSION", ".*")/APP_VERSION = os.getenv("APP_VERSION", "$(V)")/' project/project/settings.py
	@echo "Version updated to $(V) in:"
	@echo "  - pyproject.toml"
	@echo "  - project/settings.py"

# ============================================================================
# PRODUCTION
# ============================================================================
check-deploy:
	docker compose exec web python project/manage.py check --deploy
