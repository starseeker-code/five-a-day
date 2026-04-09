# CLAUDE.md — Project Context for AI-Assisted Development

## What is this project?

Five a Day eVolution is a Django student management system for a small English academy in Albacete, Spain. It manages students, parents, enrollments, payments, class scheduling, and automated email communications. The system is designed for 3-10 admin users managing up to 2,000 students.

## Architecture

### 4 Django apps

- **students** — People models (Student, Parent, Teacher, Group, StudentParent). No views of its own — views live in `core/views/`.
- **billing** — Financial models (SiteConfiguration, EnrollmentType, Enrollment, Payment). Contains the service layer (EnrollmentService, PaymentService, PricingService) where business logic lives.
- **comms** — No models. Email service (EmailService), email convenience functions, Celery tasks, management commands for sending emails.
- **core** — Cross-cutting models (TodoItem, HistoryLog, FunFridayAttendance, ScheduleSlot). Owns ALL views (split into 12 modules in `core/views/`), ALL templates, middleware, and URL routing for dashboard/auth/schedule.

### Key design decisions

- **Views stay in core** — while models are split across apps, all views remain in `core/views/` for simplicity. Each app's `urls.py` imports views from `core.views`.
- **Service layer in billing** — business logic (enrollment creation, payment calculation, pricing) is extracted from views/forms into `billing/services/`. Forms delegate to services.
- **SiteConfiguration is the single source of truth for pricing** — `billing/constants.py` has seed values only used when creating the initial config row.
- **Session-based custom auth** — `SimpleAuthMiddleware` uses `LOGIN_USERNAME`/`LOGIN_PASSWORD` from env vars. No Django User model.
- **Tailwind CSS via CDN** — no build tools. Custom violet palette defined in `base.html`'s Tailwind config block.
- **All JS extracted to static files** — 13 modules in `core/static/js/`. Django template variables passed via `data-*` attributes or small inline config scripts.

### Dependency flow

```text
students ← billing (FK refs)
students ← core (FunFridayAttendance, ScheduleSlot FK refs)
students ← comms (email recipient resolution)
billing ← comms (tax certificate PDF generation)
billing ← core/views (dashboard stats, payment views)
comms ← core/views (student creation triggers welcome email)
```

## How to run

```bash
cd project
poetry install
python manage.py migrate
python manage.py runserver
```

Tests: `python -m pytest tests/ -v` (uses SQLite via `project/settings_test.py`)

## Important files

| File | What it does |
| ---- | ------------ |
| `project/settings.py` | Main settings — DB config, email, Celery, middleware |
| `project/settings_test.py` | Test overrides — SQLite, simple static storage |
| `project/urls.py` | Root URL conf — includes students, billing, comms, core |
| `core/views/__init__.py` | Re-exports all views for URL routing compatibility |
| `core/templates/base.html` | Main layout — Tailwind CDN config, sidebar, header, support modal |
| `core/middleware.py` | SimpleAuthMiddleware — session-based auth |
| `core/context_processors.py` | Injects notifications, todos, history count into all templates |
| `billing/models.py` | SiteConfiguration (singleton), Enrollment, Payment + academic year helpers |
| `billing/services/enrollment_service.py` | Enrollment creation with all discount logic |
| `billing/services/payment_service.py` | Payment calculation (monthly, quarterly, discounts) |
| `comms/services/email_service.py` | EmailService class + global singleton |
| `conftest.py` | Pytest fixtures — all models + authenticated_client |

## Conventions

- **Language**: Code in English, UI/templates in Spanish. Comments are mixed.
- **Models**: Every model has explicit `db_table`. All use `created_at`/`updated_at` timestamps. BigAutoField PKs.
- **Views**: Mix of CBVs (student CRUD) and FBVs (everything else). AJAX endpoints return `JsonResponse` with `{"success": bool, ...}`.
- **Forms**: Django ModelForms for data entry. EnrollmentForm delegates to EnrollmentService.
- **Templates**: Extend `base.html`. Blocks: `title`, `sidebar_class`, `sidebar_hover`, `page_title`, `page_subtitle`, `header_actions`, `extra_css`, `content`, `modals`, `extra_js`.
- **JS**: External files in `core/static/js/`. Django data passed via `data-*` attrs on body or small `<script>window.CONFIG = {...}</script>` blocks.
- **Testing**: pytest with pytest-django. Tests in `project/tests/`. Fixtures in `conftest.py`. All view tests use `authenticated_client` fixture.

## Common tasks

### Add a new email template

1. Create `core/templates/emails/your_template.html` extending `emails/base_email.html`
2. Add a convenience function in `comms/services/email_functions.py`
3. Add a Celery task in `comms/tasks.py` if it should be async
4. Add a form view in `core/views/app_forms.py` if it needs a manual send UI
5. Add it to `comms/management/commands/test_all_emails.py` for testing

### Add a new model

1. Decide which app it belongs to (students=people, billing=money, core=cross-cutting)
2. Add the model with explicit `db_table`
3. Run `python manage.py makemigrations <app> && python manage.py migrate`
4. Add admin registration in the app's `admin.py`
5. Add fixtures in `conftest.py` and tests in `tests/test_models.py`

### Add a new view

1. Create the view function/class in the appropriate `core/views/` module
2. Add it to `core/views/__init__.py` re-exports
3. Add the URL pattern to the relevant app's `urls.py`
4. Add a test in `tests/test_views.py`

### Modify pricing logic

All pricing flows through `billing/services/`. The single source of truth is `SiteConfiguration` (DB). Never hardcode prices in views or templates — read from config.

## Gotchas

- **No `active` field on Payment** — soft-delete was planned but never implemented. Don't filter by `active=True` on Payment.
- **academic_year format** — always "YYYY-YYYY" (e.g., "2025-2026"). September starts the new year.
- **SiteConfiguration singleton** — always access via `SiteConfiguration.get_config()`, never query directly. It auto-creates with defaults if missing.
- **Celery eager mode** — without Redis, tasks run synchronously. Don't rely on task.delay() being truly async in development.
- **`#webcrumbs` removed** — the old CSS scoping wrapper is gone. If you see references to it in old code, delete them.
- **Two `search_students` views existed** — the duplicate was removed during refactoring. Only one remains.
