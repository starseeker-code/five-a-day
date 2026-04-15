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
- **PostgreSQL everywhere** — same database engine in development, testing, and production. Never use SQLite for anything other than quick local fallback (`TEST_DB_ENGINE=sqlite`).

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
uv sync --no-install-project   # Install all dependencies
make up                        # Start Docker (PostgreSQL + Django)
make test                      # Run tests (PostgreSQL)
```

### Testing — IMPORTANT

**Always use `make test`** (runs inside Docker against PostgreSQL — same database as production). Never use SQLite for testing unless explicitly asked. The `make test` command requires Docker containers to be running (`make up` first).

**IMPORTANT for AI agents:** Do NOT use `TEST_DB_ENGINE=sqlite` or run pytest directly with `python -m pytest`. Always use `make test` which runs against the Docker PostgreSQL container. If `make test` fails with connection errors, run `make up` first.

### Developer tooling

```bash
make lint              # Ruff linter
make format            # Ruff formatter
make pc-run            # Run all pre-commit hooks (dry run + auto version bump)
make test              # Run 283 tests (PostgreSQL via Docker, parallel, with coverage)
```

- **UV** for dependency management (see [docs/UV.md](docs/UV.md))
- **Ruff** for linting and formatting (`pyproject.toml [tool.ruff]`)
- **pre-commit** hooks run Ruff on every commit (`.pre-commit-config.yaml`)
- **pytest-cov** for coverage reports (`make test-coverage`)

## Important files

| File | What it does |
| ---- | ------------ |
| `project/settings.py` | Main settings — DB config, email, Celery, middleware |
| `project/settings_test.py` | Test overrides — PostgreSQL default with SQLite fallback |
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
- **Templates**: Extend `base.html`. All names in English. Blocks: `title`, `sidebar_class`, `sidebar_hover`, `page_title`, `page_subtitle`, `header_actions`, `extra_css`, `content`, `modals`, `extra_js`.
- **JS**: External files in `core/static/js/`. Django data passed via `data-*` attrs on body or small `<script>window.CONFIG = {...}</script>` blocks.
- **Testing**: pytest with pytest-django. Tests in `project/tests/`. Fixtures in `conftest.py`. All view tests use `authenticated_client` fixture. Tests run against PostgreSQL by default.

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
- **Template names are English** — all email templates were renamed from Spanish (e.g., `matricula_niño.html` → `enrollment_child.html`). Never create templates with Spanish names.
- **Version in four places** — `pyproject.toml`, `project/project/settings.py` (`APP_VERSION` default), the `README.md` header badge URL, and `uv.lock` (the project's own `[[package]]` entry). `make version x.y.z` (positional, with y/N confirmation) updates the first three with `sed` and regenerates `uv.lock` via `uv lock --quiet`. Running `make version` with no argument prints the pyproject and README badge values side-by-side and warns if they've drifted. `make pc-run`'s auto patch-bump does the same four updates, then the existing `git add uv.lock` block at the end of the target stages the regenerated lockfile so the next commit isn't blocked.
- **APP_VERSION in `.env`** — the local `.env` may contain a legacy `APP_VERSION=0.x.y` line. Either remove the line or update it — it silently overrides the default in `settings.py` at runtime.
- **`pc-run` renamed** — the old `make pre-commit-run` target is now `make pc-run`. It also auto-bumps the patch version on a clean pass (y/N prompt) and auto-stages `uv.lock` if regenerated.
- **mypy CI job needs `DJANGO_DEBUG=True`** — `django-stubs` imports `project.settings` at load time for the Django plugin. Without `DJANGO_DEBUG=True` + a dummy `DJANGO_SECRET_KEY`, the production guard at the top of `settings.py` raises `ValueError: DJANGO_SECRET_KEY debe ser cambiado en producción`. The CI `mypy` step sets both, plus `PYTHONPATH=project`, as env vars. Any new static-analysis job that imports settings will need the same.
- **Test settings disable production security redirects** — `settings_test.py` explicitly sets `SECURE_SSL_REDIRECT = False`, `SECURE_HSTS_SECONDS = 0`, `SESSION_COOKIE_SECURE = False`, `CSRF_COOKIE_SECURE = False`. Don't remove them — the Django test client speaks HTTP against `testserver`, and inheriting `SECURE_SSL_REDIRECT=True` from `settings.py` (which kicks in when `DEBUG=False`) turns every test request into a 301 to `https://testserver/...`. The overrides keep the test settings self-contained regardless of how CI configures `DJANGO_DEBUG`.
- **WhiteNoise warning is filtered** — `pytest.ini` has `filterwarnings = ignore:No directory at:UserWarning` to silence the once-per-request warning from WhiteNoise middleware when `STATIC_ROOT` (`staticfiles/`) doesn't exist. That directory only exists after `collectstatic` runs (production only), so the warning is noise in tests. Don't add `collectstatic` to the test command.

## README maintenance (MUST do at end of every work session)

The `README.md` must stay in sync with the code. At the end of any non-trivial change, verify and update these sections before handing off:

1. **Header badges** — version badge must match `pyproject.toml`
2. **Project Status table** — three rows in order Production → Testing → Development, each with branch + hosting + CI badge
3. **Recent Versions table** — keep only the **last 3** versions. Entries must include: version, date (YYYY-MM-DD), and an **extremely brief** description — one short phrase, ≤10 words, naming only the headline change. The long-form writeup (every user-visible change, subsection headings, bullets) lives in the Version History `<details>` block below, not in this table. When a new patch ships, drop the oldest row.
4. **Version History `<details>` blocks** — add a new `<details id="vXYZ" open>` block for the new version; remove the `open` attribute from the previous one. Structure: `**Subsection**` headings + bullet lists. Pull subjects from `git log` for the commits in that version.
5. **Directory Layout** — if directories, tool counts, test counts, or Make command counts changed, update them here. `tests/` line must show current test count and coverage percentage.
6. **Make Commands table** — every renamed or new `make` target must appear or be updated.
7. **Contributing → Development Workflow** — if the developer flow changed (new pre-commit behavior, new commands), update the numbered list.
8. **Table of Contents** — every new section or renamed heading must have a matching ToC entry with a valid anchor (GitHub generates anchors by lowercasing, replacing spaces with `-`, dropping non-alphanumerics except `-`).
9. **Delete stale content** — if a file or service was removed (e.g. `render.yaml`, a retired workflow), remove every reference to it. Grep the README for the name first.

**When the user invokes the `update-readme` skill**, use the staged changes (`git diff --cached`, `git status --porcelain`, `git diff --cached --stat`) to determine what changed, then apply the checklist above. Do not guess — inspect the staged diff first.

## Django Best Practices (enforced in this project)

### Models

- **Always set `db_table` explicitly** — prevents Django from auto-generating `appname_modelname` tables that break when models move between apps. Every model in this project has it.
- **Use string FK references for cross-app relationships** — `models.ForeignKey('students.Student', ...)` instead of importing the model directly. This avoids circular imports and makes app dependencies explicit.
- **Never put business logic in models** — models define data structure, properties, and simple computed fields (`is_overdue`, `full_name`, `age`). Complex logic (pricing, discount calculations, payment generation) lives in the service layer (`billing/services/`).
- **Use `select_related` and `prefetch_related` everywhere** — every queryset that touches related models should use these. Check `core/transactions.py` for examples. The N+1 query problem is the most common Django performance issue.
- **Use `models.Index` for frequently filtered fields** — Student is indexed on `group`, `active`, `birth_date`. Payment on `student`, `parent`, `payment_status`, `due_date`.
- **Use database constraints** — `UniqueConstraint` with conditions (e.g., one active enrollment per student), `unique_together`, and validators. Let the database enforce invariants, not just Python code.
- **Decimal, not Float, for money** — all financial fields use `DecimalField(max_digits=8, decimal_places=2)` with `MinValueValidator`. Never use `FloatField` for currency.

### Views

- **Fat services, thin views** — views handle HTTP (request parsing, response building, redirects, messages). Business logic lives in services. If a view function is doing calculations, move them to a service method.
- **Use `@require_http_methods` on FBVs** — explicitly declare which HTTP methods a view accepts. Every AJAX endpoint in this project uses this decorator.
- **Use `get_object_or_404` instead of try/except** — cleaner and returns a proper 404. Used throughout the project.
- **Wrap multi-model writes in `transaction.atomic()`** — student creation (Student + StudentParent + Enrollment + Payment) uses this. If any step fails, everything rolls back.
- **Return consistent JSON for AJAX** — always `{"success": True/False, ...}` or `{"valid": True/False, ...}`. Frontend code depends on this contract.
- **Don't import models at module level in views if it causes circular imports** — use lazy imports inside the function body when needed (see `StudentCreateView.form_valid`).

### Forms

- **Forms validate, services execute** — `EnrollmentForm.clean()` validates input. `EnrollmentService.create_enrollment()` does the actual creation. The form's `create_enrollment()` method is a thin bridge.
- **Use Django's form validation** — `clean_<field>()` methods for per-field validation, `clean()` for cross-field validation. Don't validate in views.
- **Set `input_formats` for date fields** — this project accepts both `%Y-%m-%d` (HTML5 date input) and `%d/%m/%Y` (Spanish format).

### Templates

- **Extend, don't repeat** — every authenticated page extends `base.html`. Use blocks for customization.
- **Keep templates logic-light** — complex conditionals and calculations should happen in the view's context, not in `{% if %}` chains in templates.
- **Pass Django data to JS via data attributes or config objects** — never embed `{% url %}` or `{{ variable }}` inside external JS files. Use `data-*` attributes on HTML elements or a small inline `<script>window.CONFIG = {...}</script>`.
- **All template filenames in English** — `enrollment_child.html`, not `matricula_niño.html`.

### Testing

- **Test against PostgreSQL** — SQLite has different behavior for constraints, transactions, and date handling. Always test against the same database you deploy to. Use `make test-sqlite` only for quick iteration.
- **Use fixtures in conftest.py** — shared fixtures (`student`, `parent`, `group`, `teacher`, `active_enrollment`, `pending_payment`, `authenticated_client`) avoid repetition.
- **Test at three levels** — model tests (data logic), service tests (business logic), view tests (HTTP behavior). Don't test Django internals.
- **Use `pytest.mark.django_db`** — either per-test or as `pytestmark` at module level. Without it, tests can't access the database.
- **Use `authenticated_client` fixture for view tests** — it pre-sets the session authentication that `SimpleAuthMiddleware` checks.
- **Parametrize repetitive tests** — error pages and email form views use `@pytest.mark.parametrize` to avoid duplicating test functions.

### Security

- **Never trust user input** — all form data goes through Django forms with validation. Raw `request.POST.get()` is only used for simple string values in AJAX handlers.
- **CSRF protection on every POST** — Django's `CsrfViewMiddleware` is active. JS uses `getCsrfToken()` from cookies for AJAX. The only `@csrf_exempt` is the health check.
- **Don't expose secrets in templates** — `LOGIN_PASSWORD`, API keys, etc. are never rendered in HTML. Google OAuth credentials are only used server-side.
- **Validate relationships before writes** — creating a payment validates that the student-parent relationship exists. This prevents orphaned records.
- **Use `PROTECT` for foreign keys** — deleting a Teacher won't cascade-delete their Groups. Deleting a Student won't cascade-delete Payments. Only explicit `CASCADE` where appropriate (StudentParent through model).

### Performance

- **Avoid N+1 queries** — use `select_related` (FK/OneToOne) and `prefetch_related` (M2M/reverse FK). The `transactions.py` module provides pre-built optimized querysets.
- **Don't evaluate querysets at module level** — the old `all_students = Student.objects.filter(...)` in `transactions.py` was evaluated once at import time. Now it's wrapped in functions that return fresh querysets per request.
- **Paginate large result sets** — the database view and payment list use Django's `Paginator`. The history dropdown uses offset-based AJAX pagination.
- **Use `values_list` when you only need IDs** — `student.parents.values_list('id', flat=True)` instead of fetching full Parent objects.
- **Cache the SiteConfiguration** — `SiteConfiguration.get_config()` does a single DB query per call. For request-scoped reuse, store the result in a local variable.

### Email

- **Use the EmailService class** — never call `django.core.mail.send_mail()` directly. The `EmailService` handles HTML rendering, inline images, attachments, and logging.
- **All emails have a convenience function** — `comms/services/email_functions.py` provides typed functions like `send_birthday_email(recipient, name)` instead of raw template/context calls.
- **Celery tasks for async sends** — student creation queues a welcome email via `send_welcome_email_task.delay()`. If Celery isn't available (no Redis), it runs synchronously via eager mode.
- **Always set `fail_silently=True` for non-critical emails** — a failed birthday email should not crash the application.

### Code Organization

- **Explicit imports only** — never `from app.models import *`. Every import names what it needs.
- **Cross-app references use string FKs** — `'students.Student'` in billing models, not `from students.models import Student`.
- **Keep `__init__.py` files minimal** — the `core/views/__init__.py` re-exports are an exception for URL routing compatibility. Other `__init__.py` files should be empty.
- **Group related functionality** — all pricing logic in `billing/services/`, all email logic in `comms/services/`, all view logic in `core/views/`. Don't scatter related code across apps.
- **Management commands import from services** — `generate_payments` command calls `PaymentService` methods. Commands are thin wrappers around service logic.
