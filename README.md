# Five a Day eVolution

<p align="center">
  <img src="docs/resources/logo.png" alt="Five a Day Logo" width="320">
  <br>
  <em>Student Management System for Five a Day English Academy</em>
  <br>
  <em>Albacete, Spain</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v1.0.5-brightgreen?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/python-3.12+-blue?style=for-the-badge" alt="Python">
  <img src="https://img.shields.io/badge/django-5.2-green?style=for-the-badge" alt="Django">
  <img src="https://img.shields.io/badge/postgresql-16-336791?style=for-the-badge" alt="PostgreSQL">
  <a href="https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml"><img src="https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://codecov.io/gh/starseeker-code/five-a-day"><img src="https://codecov.io/gh/starseeker-code/five-a-day/branch/main/graph/badge.svg" alt="Coverage"></a>
</p>

---

Built to centralize student records, automate billing cycles, and streamline parent communication for a small English academy managing up to 2,000 students with 3-10 admin users.

**Key objectives:**
- Replace manual Google Sheets with a searchable, relational database
- Automate monthly and quarterly payment generation and tracking
- Streamline parent communication with 12 templated email types (previews, test sends, bulk sends)
- Provide an operational dashboard for daily tasks: pending payments, birthdays, upcoming events, todos
- Support the full academic year cycle (September enrollment through June closure)

### Project Status

Live status for each environment is pulled from GitHub Actions — the badges below reflect the real state of CI on each branch.

| Environment | Branch | Hosting | CI Status |
|-------------|--------|---------|-----------|
| **Production** | `main` | GCP Cloud Run + Cloud SQL (PostgreSQL 16), `europe-southwest1` | [![Production CI](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml?query=branch%3Amain) |
| **Testing (QA)** | `testing` | GCP Compute Engine e2-micro (free tier), Docker Compose | [![Testing CI](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml/badge.svg?branch=testing)](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml?query=branch%3Atesting) |
| **Development** | `development` | Local machine via `make up` (Docker Compose) | [![Development CI](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml/badge.svg?branch=development)](https://github.com/starseeker-code/five-a-day/actions/workflows/ci.yml?query=branch%3Adevelopment) |

| Version | Date | Description |
|---------|------|-------------|
| **v1.0.5** | 2026-04-15 | GitHub Actions CI/CD pipeline (lint, typecheck, tests, CodeQL, Dependabot), auto-merge `development` → `testing` with 24 h delay + auto-PR to `main`, email notifications, branch protection rules for public repo hardening, `make pc-run` auto-stages regenerated `uv.lock` |
| v1.0.4 | 2026-04-15 | Inspirational quote generator on `/home` (48 h cookie rotation), GCP deployment plan ([DEPLOYMENT.md](DEPLOYMENT.md)), Celery worker + beat containers, cleaned legacy Render config, `make version x.y.z` positional arg with confirmation guard, `make pc-run` (renamed from `pre-commit-run`) with auto version bump |
| v1.0.3 | 2026-04-14 | Test coverage raised to **70 %** — 13 new test files across auth views, comms services, app forms, constants, create payment views, exports, forms, parent views, payment views, schedule views, student forms, student views, transactions |

---

## Table of Contents

- [Five a Day eVolution](#five-a-day-evolution)
    - [Project Status](#project-status)
  - [Table of Contents](#table-of-contents)
  - [Version History \& Roadmap](#version-history--roadmap)
    - [Roadmap](#roadmap)
      - [v1.1 — Waiting List \& Group Capacity](#v11--waiting-list--group-capacity)
      - [v1.2 — Google Sheets Integration](#v12--google-sheets-integration)
      - [v1.3 — PDF Invoice Generation](#v13--pdf-invoice-generation)
      - [v1.4 — Celery + Redis Deployment](#v14--celery--redis-deployment)
      - [v1.5 — Expense Tracking](#v15--expense-tracking)
      - [v1.6 — Multi-User Permissions](#v16--multi-user-permissions)
      - [v1.7 — Advanced Reporting \& Analytics](#v17--advanced-reporting--analytics)
      - [v1.8 — SMS Notifications (Twilio)](#v18--sms-notifications-twilio)
      - [v1.9 — Parent Portal](#v19--parent-portal)
      - [v1.10 — Audit Log \& Security Hardening](#v110--audit-log--security-hardening)
      - [v1.11 — Stripe Payment Integration](#v111--stripe-payment-integration)
      - [v1.12 — Mobile Optimization \& PWA](#v112--mobile-optimization--pwa)
  - [Tech Stack](#tech-stack)
    - [Backend](#backend)
    - [Frontend](#frontend)
    - [Infrastructure \& Deployment](#infrastructure--deployment)
    - [Python Dependencies](#python-dependencies)
  - [Database Schema](#database-schema)
    - [ER Diagram](#er-diagram)
    - [Key Constraints](#key-constraints)
  - [Development \& Docker](#development--docker)
    - [Quick Start](#quick-start)
    - [.env template](#env-template)
    - [Make Commands](#make-commands)
    - [Environment Configuration](#environment-configuration)
    - [Environment Variables Reference](#environment-variables-reference)
    - [App Versioning](#app-versioning)
  - [Project Structure \& Architecture](#project-structure--architecture)
    - [Architecture Overview](#architecture-overview)
    - [App Dependency Flow](#app-dependency-flow)
    - [Directory Layout](#directory-layout)
    - [App: core](#app-core)
    - [App: students](#app-students)
    - [App: billing](#app-billing)
    - [App: comms](#app-comms)
    - [Design Decisions](#design-decisions)
  - [Features by View](#features-by-view)
    - [Home (Dashboard)](#home-dashboard)
    - [Students](#students)
    - [Student Create](#student-create)
    - [Student Detail \& Update](#student-detail--update)
    - [Payments](#payments)
    - [Schedule](#schedule)
    - [Fun Friday](#fun-friday)
    - [Apps (Email Tools)](#apps-email-tools)
    - [Management](#management)
    - [Database (All Info)](#database-all-info)
    - [Login](#login)
  - [Testing](#testing)
    - [Testing Overview](#testing-overview)
    - [Model Tests](#model-tests)
    - [Service Tests](#service-tests)
    - [View Tests](#view-tests)
  - [Migrations](#migrations)
  - [Security](#security)
    - [Authentication](#authentication)
    - [Session \& Cookie Configuration](#session--cookie-configuration)
    - [CSRF Protection](#csrf-protection)
    - [Transport Security (HTTPS)](#transport-security-https)
    - [Security Headers](#security-headers)
    - [Infrastructure \& Deployment](#infrastructure--deployment-1)
      - [Docker](#docker)
      - [Google Cloud Run](#google-cloud-run)
    - [Secrets Management](#secrets-management)
    - [Email Security](#email-security)
    - [Data Protection \& Input Validation](#data-protection--input-validation)
    - [Logging \& Monitoring](#logging--monitoring)
    - [Future Security Improvements](#future-security-improvements)
  - [Testing Environment (QA)](#testing-environment-qa)
    - [What is the testing environment?](#what-is-the-testing-environment)
    - [How to access it](#how-to-access-it)
    - [What you can test](#what-you-can-test)
    - [How to report a problem](#how-to-report-a-problem)
    - [Error pages you might see](#error-pages-you-might-see)
    - [For developers: how the QA environment works](#for-developers-how-the-qa-environment-works)
      - [Access control for /testing/](#access-control-for-testing)
  - [CI/CD \& GitHub Actions](#cicd--github-actions)
    - [Pipeline Overview](#pipeline-overview)
    - [Branch Strategy](#branch-strategy)
    - [Workflows](#workflows)
    - [Automated Flows](#automated-flows)
    - [Branch Protection — `main`](#branch-protection--main)
    - [Branch Protection — `testing`](#branch-protection--testing)
    - [Public Repository Hardening](#public-repository-hardening)
    - [Required GitHub Secrets](#required-github-secrets)
    - [Email Notifications](#email-notifications)
    - [Dependabot](#dependabot)
    - [CodeQL Security Scanning](#codeql-security-scanning)
  - [Contributing](#contributing)
    - [Development Workflow](#development-workflow)
    - [Code Conventions](#code-conventions)
    - [Adding a Feature](#adding-a-feature)
  - [License](#license)

---

## Version History & Roadmap

<details id="v105" open>
<summary><strong>v1.0.5 — CI/CD Pipeline & Public Repo Hardening (current)</strong></summary>

**GitHub Actions CI/CD** (new — see [docs/GITHUB.md](docs/GITHUB.md))

- `ci.yml` — three parallel jobs on every push/PR: Ruff + Bandit lint, mypy type check, pytest against a PostgreSQL 16 service container with coverage uploaded to Codecov
- `auto-merge.yml` — hourly cron that merges `development` → `testing` after 24 h of inactivity and CI passing, then auto-creates a PR `testing` → `main`
- `codeql.yml` — weekly Python security analysis (OWASP Top 10, Django-specific queries)
- `notify-production.yml` — emails `hellofiveaday@gmail.com` on every push to `main` with commit info and `gcloud` deploy instructions
- Owner email notifications when `development` → `testing` merge lands and a PR is opened to `main`
- `dependabot.yml` — grouped weekly Python and GitHub Actions updates targeting `development`
- `CODEOWNERS` — auto-request reviews from both owner accounts

**Public-repo hardening**

- Branch protection rules documented for `main` (14 protections) and `testing` (minimal)
- Secret scanning + push protection + CodeQL enabled (all free for public repos)
- Fork PR workflow restriction, read-only default workflow permissions, block-approvals-from-Actions
- `SECURITY.md` + `CODEOWNERS` + `LICENSE` required-file checklist in [docs/GITHUB.md](docs/GITHUB.md)

**Developer tooling**

- `make pc-run` auto-stages regenerated `uv.lock` as the final step — next `git commit` is no longer blocked by the lock file

</details>

<details id="v104">
<summary><strong>v1.0.4 — GCP Migration Plan, Quote Generator, Celery</strong></summary>

**GCP migration plan** (new — see [DEPLOYMENT.md](DEPLOYMENT.md))

- Full Cloud Run + Cloud SQL architecture documented
- Three environments: local Docker (dev), Compute Engine e2-micro free tier (testing), Cloud Run + Cloud SQL (production)
- Cost estimate: ~$15-27/month for production, $0/month for testing
- Celery replacement strategy using Cloud Scheduler + Cloud Run Jobs
- Cleaned legacy Render config — `render.yaml` removed; commented nginx and pgAdmin services removed from `docker-compose.yml`

**Dashboard enhancement**

- Inspirational quote generator on `/home` — fetches two daily quotes from `zenquotes.io`, stores them in a 48 h cookie, rotates daily (day 0 shows quote 1, day 1+ shows quote 2), graceful fallback to the default Spanish subtitle on API failure

**Developer tooling**

- `make version x.y.z` — positional argument (replaces `V=x.y.z`) with confirmation guard before writing
- `make pc-run` — renamed from `pre-commit-run`; after a clean pass, prompts to auto-increment the patch version in `pyproject.toml` and `project/settings.py`

**Celery**

- Celery worker and beat containers added to `docker-compose.yml` with correct permissions and health checks
- Several payment and enrollment issues fixed

</details>

<details id="v103">
<summary><strong>v1.0.3 — Test Coverage Expansion (70%)</strong></summary>

**Testing**

- 40+ new tests added across 13 new test files — overall suite around 280+ tests
- Coverage raised to **70%** across `core`, `students`, `billing`, `comms`
- New test files: `test_auth_views.py`, `test_app_form_views.py`, `test_constants.py`, `test_create_payment_views.py`, `test_exports.py`, `test_forms.py`, `test_parent_views.py`, `test_payment_views.py`, `test_schedule_views.py`, `test_student_forms.py`, `test_student_views.py`, `test_transactions.py`
- Additional parametrized test cases for email-form views and error pages

**Coverage tooling**

- Coverage badge pulled dynamically from Codecov (CI workflow uploads `coverage.xml` on every run)
- `make coverage-badge` retained for offline SVG generation

</details>

<details id="v102">
<summary><strong>v1.0.2 — UV Migration & Developer Tooling</strong></summary>

**Dependency management**

- Replaced Poetry with UV (see [docs/UV.md](docs/UV.md))
- `uv.lock` replaces `poetry.lock`
- All Make commands updated to use `uv run`

**Developer tooling**

- **Ruff** — unified lint + format (replaces flake8, isort, black)
- **mypy** with `django-stubs` — static type checking
- **bandit** — Python security linter
- **pip-audit** — dependency CVE scanning
- **pytest-xdist** — parallel test execution (`-n auto`)
- **pytest-randomly** — randomized test order with reproducible seeds
- **pytest-cov** — coverage reports (HTML + XML + terminal)
- **pre-commit** hooks — Ruff, mypy, bandit on every commit

All tools configured in `pyproject.toml` — single source of truth.

</details>

<details id="v101t">
<summary><strong>v1.0.1t — QA Testing Environment</strong></summary>

**Testing infrastructure**
- QA Docker Compose overlay (`docker-compose.testing.yml`) — Gunicorn, `DEBUG=False`, separate DB volume
- `.env.testing` with dedicated credentials and `DJANGO_ENV=testing`
- Database seeding command (`seed_testdata`) — 15+ students, parents, enrollments, payments
- HTTPS documentation (`HTTPS.md`) — local Docker (Nginx + self-signed cert) and GCP Cloud Run

**Testing dashboard (`/testing/`)**
- Project info card — version, environment, last commit (branch, hash, author, date)
- Error reporting toggle — sends unhandled exceptions to SUPPORT_EMAIL with full traceback
- Database seeding UI — seed or wipe-and-reseed via AJAX
- Backlog — create tasks with priority, each emailed to support automatically

**Access control**
- `qa_access_required` decorator in `core/decorators.py`
- Gated by `DJANGO_ENV=testing` + `DEBUG=False` + session username matches `QA_TESTING_USERNAME`
- Returns 404 (not 403) for unauthorized users — page appears not to exist
- Sidebar icon hidden for all non-QA users via context processor

**Bug fixes**
- Added `STATICFILES_DIRS` for `project/static/` — email CSS was missing from collectstatic manifest
- Added `SECURE_PROXY_SSL_HEADER` for HTTPS behind reverse proxies
- `QAErrorEmailMiddleware` for automated error reporting to support email

</details>

<details id="v100">
<summary><strong>v1.0.0 — Architecture Refactor & Test Suite</strong></summary>

**Architecture**
- Split monolithic `core` app into 4 apps: `students`, `billing`, `comms`, `core`
- Created service layer: EnrollmentService, PaymentService, PricingService
- Split 3,648-line views.py into 12 focused modules
- Fixed module-level querysets, wildcard imports, dual pricing source of truth

**Frontend**
- Replaced 1,178-line pre-compiled Tailwind with CDN + custom violet palette config
- Extracted ~1,400 lines of inline JS into 13 static modules
- Removed `#webcrumbs` CSS scoping wrapper
- base.html: 610 lines reduced to 305 lines

**Testing**
- 132 pytest tests: 41 model, 26 service, 65 view tests
- Tests run against PostgreSQL (same as production)
- Found and fixed Payment `active` field bug

**Templates**
- Renamed all Spanish-named email templates to English (e.g., `matricula_niño.html` -> `enrollment_child.html`)

**Documentation**
- Comprehensive README with all sections
- Per-app README.md files (core, students, billing, comms)
- CLAUDE.md for AI-assisted development
- DEPLOYMENT.md for Google Cloud Platform

</details>

<details id="v0302">
<summary><strong>v0.30.2 — Docker & History System</strong></summary>

- Docker Compose with PostgreSQL 16 + Django
- Makefile with 40+ commands for development workflow
- HistoryLog system for tracking user actions (capped at 1,000 entries)
- GDPR tracking for adult students
- Improved entrypoint script for Docker

</details>

<details id="v0290">
<summary><strong>v0.29.0 — Enrollment & Email System</strong></summary>

- Enrollment system with 3 plans (monthly full/part-time, quarterly)
- Discount engine: language cheque, sibling, quarterly, June end-of-year
- Adult student support with separate pricing
- 12 email templates with preview and test-send
- Fun Friday attendance tracking
- Support ticket system

</details>

### Roadmap

<details id="roadmap">
<summary><strong>Click to expand full roadmap (v1.1 — v1.12)</strong></summary>

#### v1.1 — Waiting List & Group Capacity

Students can be created with a `waiting_list` flag instead of being immediately enrolled. When a group has capacity (a student leaves), waiting list students are surfaced for assignment.

- New `is_waiting` boolean on Student model
- `max_students` soft limit on Group model with `student_count` tracking
- Notification when a student is deactivated and a group drops below capacity
- Waiting list management view: filter by group preference, priority by creation date
- Quick-assign flow: from waiting list or student creation, assign to group with one click
- Dashboard widget showing groups with available spots and waiting students

#### v1.2 — Google Sheets Integration

Automatic export of student/payment data to Google Sheets for existing spreadsheet workflows. Read and write via `gspread` using already-configured Google OAuth credentials.

#### v1.3 — PDF Invoice Generation

Proper PDF generation using WeasyPrint. Invoice/receipt PDFs for individual payments and quarterly summaries. Replace the current HTML-fallback tax certificate.

#### v1.4 — Celery + Redis Deployment

Full async task processing with Redis broker. Move all email sends to background tasks. Add Celery Beat for scheduled jobs: daily birthday emails at 8:00 AM, monthly payment generation on the 1st, monthly reports on the 28th.

#### v1.5 — Expense Tracking

Track academy expenses (rent, supplies, salaries) with categories, recurring templates, and monthly totals. Income-vs-expense dashboard widget showing profitability.

#### v1.6 — Multi-User Permissions

Replace SimpleAuthMiddleware with Django's built-in auth. Roles: admin (full access), teacher (read-only students + schedule), assistant (everything except configuration).

#### v1.7 — Advanced Reporting & Analytics

Monthly and yearly financial reports with charts. Student retention analytics. Payment collection rates. Group utilization metrics. Exportable to PDF.

#### v1.8 — SMS Notifications (Twilio)

SMS as an alternative notification channel for payment reminders and urgent communications. Opt-in per parent. Fallback to email when SMS fails.

#### v1.9 — Parent Portal

Read-only web portal for parents to view enrollment status, payment history, upcoming events, and download receipts/certificates. Separate authentication from admin panel.

#### v1.10 — Audit Log & Security Hardening

Full audit trail for all data changes (who changed what, when). Rate limiting on login and API endpoints. Two-factor authentication for admin users.

#### v1.11 — Stripe Payment Integration

Online payment via Stripe. Parents receive payment links by email. Automatic reconciliation with pending payments. Receipts generated on completion.

#### v1.12 — Mobile Optimization & PWA

Progressive Web App support: installable on mobile, offline-capable dashboard, push notifications for overdue payments and birthdays.

</details>

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Runtime |
| Django | 5.2.5 | Web framework |
| PostgreSQL | 16 (Alpine) | Database (production, development, and testing) |
| Celery | 5.5.3 | Async task queue (eager mode without Redis, full async with Redis in v1.4) |
| Celery Beat | (bundled with Celery) | Scheduled task execution (birthday emails, payment generation — v1.4) |
| Redis | 7 (Alpine) | Message broker for Celery (planned, v1.4) |
| Gunicorn | 21.2.0 | Production WSGI server |
| WhiteNoise | 6.11.0 | Static file serving in production |

### Frontend

| Technology | Purpose |
|-----------|---------|
| [Tailwind CSS](https://tailwindcss.com/) (CDN) | Utility-first CSS with custom violet primary palette |
| [Google Fonts](https://fonts.google.com/) | Material Symbols Outlined (icons), Montserrat Alternates (login), Parisienne (login accent) |
| Vanilla JavaScript | 13 static modules — zero build tools, no framework |

### Infrastructure & Deployment

| Technology | Purpose |
|-----------|---------|
| Docker | Multi-stage build, non-root `django` user |
| Docker Compose | Service orchestration (PostgreSQL + Django) |
| Google Cloud Platform | Production hosting: Cloud Run + Cloud SQL |
| Gmail SMTP | Email sending (app password authentication) |
| Google OAuth 2.0 | Optional admin authentication |
| Make | 45+ development commands |

### Python Dependencies

| Package | Purpose |
|---------|---------|
| `django-cors-headers` | CORS handling for future API consumers |
| `django-filter` | Query filtering utilities |
| `django-extensions` | Development utilities (shell_plus, graph_models) |
| `django-gsheets` + `gspread` | Google Sheets integration (v1.2) |
| `django-redis` | Redis cache backend (v1.4) |
| `django-storages` | Cloud storage backends (future) |
| `pandas` | Data processing for exports |
| `openpyxl` | Excel file generation (.xlsx) |
| `httpx` | HTTP client for external API calls |
| `psycopg2-binary` | PostgreSQL database adapter |
| `dj-database-url` | Database URL parsing for cloud deployments |
| `python-dotenv` | Environment variable loading from .env |
| `markdown` | Markdown rendering |
| `pytest` + `pytest-django` | Testing framework |
| `pytest-xdist` | Parallel test execution (`-n auto`) |
| `pytest-randomly` | Randomized test ordering (catches order-dependent bugs) |
| `pytest-cov` + `coverage-badge` | Coverage reporting + SVG badge generation |

### Developer Tooling

| Tool | Purpose |
|------|---------|
| [UV](https://docs.astral.sh/uv/) | Dependency management (replaces Poetry). PEP 621, `uv.lock`. See `docs/UV.md` |
| [Ruff](https://docs.astral.sh/ruff/) | Linting + formatting (replaces flake8, black, isort). Config in `pyproject.toml` |
| [mypy](https://mypy-lang.org/) + `django-stubs` | Static type checking with Django ORM support |
| [bandit](https://bandit.readthedocs.io/) | Security linter (hardcoded secrets, SQL injection, etc.) |
| [pip-audit](https://github.com/pypa/pip-audit) | Dependency vulnerability scanning against PyPI CVE database |
| [pre-commit](https://pre-commit.com/) | Git hooks: ruff, ruff-format, mypy, bandit |

---

## Database Schema

### ER Diagram

```mermaid
erDiagram
    Teacher {
        int id PK
        string first_name
        string last_name
        string email UK
        string phone
        bool active
        bool admin
    }

    Group {
        int id PK
        string group_name UK
        string color
        int teacher_id FK
        bool active
    }

    Parent {
        int id PK
        string first_name
        string last_name
        string dni UK
        string phone
        string email
        string iban
    }

    Student {
        int id PK
        string first_name
        string last_name
        date birth_date
        bool is_adult
        string email
        string phone
        string school
        text allergies
        bool gdpr_signed
        int group_id FK
        bool active
        date withdrawal_date
        text withdrawal_reason
    }

    StudentParent {
        int id PK
        int student_id FK
        int parent_id FK
    }

    SiteConfiguration {
        int id PK
        decimal children_enrollment_fee
        decimal adult_enrollment_fee
        decimal full_time_monthly_fee
        decimal part_time_monthly_fee
        decimal adult_group_monthly_fee
        decimal language_cheque_discount
        decimal quarterly_enrollment_discount
        decimal sibling_discount
        decimal june_discount
        decimal full_year_bonus
    }

    EnrollmentType {
        int id PK
        string name UK
        string display_name
        decimal base_amount_full_time
        decimal base_amount_part_time
        bool active
    }

    Enrollment {
        int id PK
        int student_id FK
        int enrollment_type_id FK
        date enrollment_period_start
        date enrollment_period_end
        string academic_year
        string schedule_type
        string payment_modality
        bool has_language_cheque
        bool is_sibling_discount
        decimal enrollment_amount
        decimal discount_percentage
        decimal final_amount
        string status
        date enrollment_date
    }

    Payment {
        int id PK
        int student_id FK
        int parent_id FK
        int enrollment_id FK
        string payment_type
        string payment_method
        decimal amount
        string payment_status
        date due_date
        date payment_date
        string concept
        string reference_number
    }

    TodoItem {
        int id PK
        string text
        date due_date
    }

    HistoryLog {
        int id PK
        string action
        string message
        string icon
        datetime created_at
    }

    ScheduleSlot {
        int id PK
        int row
        int day
        int col
        int group_id FK
    }

    FunFridayAttendance {
        int id PK
        int student_id FK
        date date
    }

    Teacher ||--o{ Group : "teaches"
    Group ||--o{ Student : "contains"
    Student }o--o{ Parent : "has parents"
    Student ||--o{ StudentParent : ""
    Parent ||--o{ StudentParent : ""
    Student ||--o{ Enrollment : "enrolls in"
    EnrollmentType ||--o{ Enrollment : "type of"
    Student ||--o{ Payment : "pays"
    Parent ||--o{ Payment : "responsible for"
    Enrollment ||--o{ Payment : "covers"
    Group ||--o{ ScheduleSlot : "assigned to"
    Student ||--o{ FunFridayAttendance : "attends"
```

### Key Constraints

| Constraint | Model | Rule |
|-----------|-------|------|
| Singleton | SiteConfiguration | Always pk=1, cannot be deleted |
| Unique active | Enrollment | Only one active enrollment per student |
| Unique pair | StudentParent | (student, parent) |
| Unique pair | FunFridayAttendance | (student, date) |
| Unique triple | ScheduleSlot | (row, day, col) |
| Unique | Teacher.email, Group.group_name, Parent.dni, EnrollmentType.name | |

---

## Development & Docker

### Quick Start

```bash
# Clone the repository
git clone https://github.com/starseeker-code/five-a-day.git
cd five-a-day

# Create the .env file — copy the template below into `.env` and fill in the blanks
touch .env
```

Paste the template from [.env template](#env-template) into your new `.env` file and fill in the empty values.

**Docker (recommended):**

```bash
make build             # Build images
make up                # Start PostgreSQL + Redis + Django + Celery → http://localhost:8000
make migrate           # Apply migrations (first time only)
```

**Local development (no Docker):**

```bash
uv sync                # Install dependencies
cd project
python manage.py migrate
python manage.py runserver
```

> **Important**: The `.env` file controls whether the app runs in production or development mode. Before starting, set at minimum:
> - `DJANGO_ENV=development` — enables development behaviors (auto superuser, no collectstatic)
> - `DJANGO_DEBUG=true` — enables Django debug mode, detailed error pages
> - `POSTGRES_PASSWORD` — required for database connection
> - `DJANGO_SECRET_KEY` — generate with `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`

### .env template

`.env` is gitignored and never committed. The template below is the authoritative structure — copy it into your new `.env` file, then fill in the empty values with your own secrets. Defaults that are safe to keep as-is are already filled in.

```bash
# ============================================================================
# DJANGO SETTINGS
# ============================================================================
DJANGO_ENV=development          # production | development
DJANGO_DEBUG=True
SECURE_SSL_REDIRECT=False
# Generate with: python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
DJANGO_SECRET_KEY=
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# ============================================================================
# LOGGING
# ============================================================================
LOG_LEVEL=INFO
DJANGO_LOG_LEVEL=INFO

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================
DATABASE=postgres               # sqlite | postgres
POSTGRES_DB=fiveaday_db
POSTGRES_USER=fiveaday_user
# Generate with: openssl rand -base64 32
POSTGRES_PASSWORD=
POSTGRES_HOST=db                # `db` in Docker, `localhost` outside
POSTGRES_PORT=5432

# ============================================================================
# SUPERUSER (auto-created on first boot if all three are set)
# ============================================================================
DJANGO_SUPERUSER_USERNAME=
DJANGO_SUPERUSER_EMAIL=
DJANGO_SUPERUSER_PASSWORD=

# ============================================================================
# EMAIL CONFIGURATION (Gmail SMTP + App Password)
# ============================================================================
EMAIL_HOST_USER=                # your-academy@gmail.com
EMAIL_SECRET=                   # 16-char Gmail App Password
SUPPORT_EMAIL=                  # where support tickets are sent
EMAIL_TEST_1=                   # dev test recipient 1
EMAIL_TEST_2=                   # dev test recipient 2

# ============================================================================
# CELERY / REDIS
# ============================================================================
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ============================================================================
# AUTHENTICATION (session-based, until the Django User model is adopted in v1.6)
# ============================================================================
LOGIN_USERNAME=fiveaday
LOGIN_PASSWORD=

# ============================================================================
# GOOGLE OAUTH
# ============================================================================
# Create at https://console.cloud.google.com/ → APIs & Services → Credentials
# Authorised redirect URI: http://localhost:8000/auth/google/callback/
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback/

# ============================================================================
# ACADEMY BUSINESS INFO (prefilled in payment-reminder email forms)
# ============================================================================
ACADEMY_IBAN=
ACADEMY_IBAN_HOLDER=
ACADEMY_PHONE=
ACADEMY_WHATSAPP=
```

**Note**: do not include `VERSION=` in your `.env` — it is deprecated. The app version is derived from `pyproject.toml` (and overridable via `APP_VERSION`).

### Make Commands

Run `make` or `make help` for the full list. Key commands:

| Command | Description |
|---------|-------------|
| **Lifecycle** | |
| `make up` | Start all services (detached) |
| `make down` | Stop and remove containers |
| `make dev` | Start in foreground (logs visible) |
| `make rebuild` | Full rebuild (no cache) + start |
| **Django** | |
| `make shell` | Django shell in container |
| `make migrate` | Apply migrations |
| `make makemigrations` | Create migrations (all 4 apps) |
| `make check` | Django system checks |
| **Database** | |
| `make dbshell` | PostgreSQL shell |
| `make backup` | Dump DB to backups/ |
| `make reset-db` | Recreate database (destructive!) |
| **Testing** | |
| `make test` | Run all tests in Docker (PostgreSQL) |
| `make test-local` | Run tests locally against Docker PostgreSQL |
| `make test-sqlite` | Run tests with SQLite (no Docker needed) |
| `make test-coverage` | Tests with HTML coverage report |
| `make test-models` | Only model tests |
| `make test-services` | Only service tests |
| `make test-views` | Only view tests |
| `make test-fast` | Stop on first failure |
| `make test-k K=payment` | Run tests matching keyword |
| **Versioning** | |
| `make version 1.1.0` | Update version in `pyproject.toml` + `settings.py` (with y/N confirmation) |
| `make version` | Show current version |
| **Developer Tooling** | |
| `make lint` / `make lint-fix` | Run Ruff linter (optionally auto-fix) |
| `make format` / `make format-check` | Run Ruff formatter |
| `make mypy` | Run mypy type checker |
| `make bandit` | Run bandit security linter |
| `make audit` | `pip-audit` — scan deps for CVEs |
| `make pc-run` | Run pre-commit on all files; on clean pass, offer to auto-bump patch version; auto-stages regenerated `uv.lock` |
| `make pre-commit-install` | Install the git pre-commit hook |
| **Email & Payments** | |
| `make send-test-email` | Send test birthday email |
| `make test-all-emails` | List all email templates |
| `make generate-payments` | Generate current month's payments |
| `make generate-payments-dry` | Preview without creating |
| **Health** | |
| `make health` | Full health check (Django + DB + HTTP) |
| `make check-deploy` | Django deployment checklist |

### Environment Configuration

The project supports three environments, controlled by `DJANGO_ENV` and `DJANGO_DEBUG`:

| Environment | `DJANGO_ENV` | `DJANGO_DEBUG` | Database | Static Files | Use Case |
|------------|-------------|---------------|----------|-------------|----------|
| **Production** | `production` | `false` | PostgreSQL (Cloud SQL) | WhiteNoise + collectstatic | Live deployment |
| **Development** | `development` | `true` | PostgreSQL (Docker) | Django dev server | Local coding |
| **Testing** | (via settings_test.py) | `false` | PostgreSQL (Docker) | Simple storage | `make test` |

> **Defaults are production-safe**: `DJANGO_DEBUG` defaults to `false` and `DJANGO_ENV` defaults to `development`. In production, always set `DJANGO_ENV=production` and ensure `DJANGO_SECRET_KEY` is a strong random value.

The database is **always PostgreSQL** — in Docker development, in tests, and in production. Tests run against the same Docker PostgreSQL container to ensure realistic behavior. For quick local test runs without Docker, use `make test-sqlite`.

### Environment Variables Reference

The table below describes every variable in the [.env template](#env-template) above, plus a few advanced overrides not included in the template. See the template for the full `.env` structure.

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| **Django core** | | | |
| `DJANGO_ENV` | Environment: `development` / `production` / `testing` | No | `development` |
| `DJANGO_DEBUG` | Debug mode: `true` / `false` | No | `false` |
| `DJANGO_SECRET_KEY` | Secret key | **Yes in production** | dev fallback |
| `DJANGO_ALLOWED_HOSTS` | Comma-separated hosts | No | `localhost,127.0.0.1` |
| `SECURE_SSL_REDIRECT` | Force HTTPS redirects | No | `True` when `DEBUG=False` |
| **Database** | | | |
| `DATABASE` | Set to `postgres` for PostgreSQL | No | `postgres` |
| `DATABASE_URL` | Full URL (Cloud deployments) | No | — |
| `POSTGRES_DB` | Database name | No | `fiveaday_db` |
| `POSTGRES_USER` | Database user | No | `fiveaday_user` |
| `POSTGRES_PASSWORD` | Database password | **Yes** | — |
| `POSTGRES_HOST` | Database host | No | `db` (Docker) |
| `POSTGRES_PORT` | Database port | No | `5432` |
| **Superuser** (auto-created on first boot when all three are set) | | | |
| `DJANGO_SUPERUSER_USERNAME` | Superuser name | No | — |
| `DJANGO_SUPERUSER_EMAIL` | Superuser email | No | — |
| `DJANGO_SUPERUSER_PASSWORD` | Superuser password | No | — |
| **Email** | | | |
| `EMAIL_HOST_USER` | Gmail address | For email features | — |
| `EMAIL_SECRET` | Gmail app password | For email features | — |
| `SUPPORT_EMAIL` | Support ticket recipient | No | — |
| `EMAIL_TEST_1` / `EMAIL_TEST_2` | Test email recipients | No | — |
| **Auth** | | | |
| `LOGIN_USERNAME` | Admin username | **Yes** | — (login refused if missing) |
| `LOGIN_PASSWORD` | Admin password | **Yes** | — (login refused if missing) |
| `QA_TESTING_USERNAME` | Extra user allowed to see `/testing/` dashboard | No (QA only) | — |
| `GOOGLE_CLIENT_ID` | OAuth client ID | For Google login | — |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret | For Google login | — |
| `GOOGLE_REDIRECT_URI` | OAuth callback URL | For Google login | auto-detected |
| `GOOGLE_ALLOWED_EMAIL` | Restrict Google login to one email | No | `EMAIL_HOST_USER` |
| **Celery / Redis** | | | |
| `CELERY_BROKER_URL` | Redis URL for Celery | No | eager mode (tasks run inline) |
| `CELERY_RESULT_BACKEND` | Redis URL for results | No | same as broker |
| **Academy business info** (prefills payment-reminder email forms) | | | |
| `ACADEMY_IBAN` | Bank account for payment reminders | No | — |
| `ACADEMY_IBAN_HOLDER` | IBAN account holder | No | — |
| `ACADEMY_PHONE` | Phone for Bizum payments | No | — |
| `ACADEMY_WHATSAPP` | WhatsApp number for reminders | No | — |
| **Logging / misc** | | | |
| `LOG_LEVEL` | App log level | No | `DEBUG` in dev, `INFO` in prod |
| `DJANGO_LOG_LEVEL` | Django framework log level | No | inherits `LOG_LEVEL` |
| `APP_VERSION` | Version string override | No | from `settings.py` default |
| `SESSION_COOKIE_AGE` | Session duration (seconds) | No | `86400` (24 h) |

### App Versioning

The app version is defined in **two places** and should be updated together:

1. **`pyproject.toml`** line 3: `version = "x.y.z"` — package metadata
2. **`project/settings.py`** line 17: `APP_VERSION = os.getenv("APP_VERSION", "x.y.z")` — runtime fallback

Use `make version x.y.z` (positional) to update both at once — it prompts `Version A will become the new version B, are you sure?` before writing. `make pc-run` also auto-bumps the patch digit on successful pre-commit if you answer `y` when asked.

The version appears in:
- `/health/` endpoint response
- Support ticket emails
- Can be overridden at runtime via the `APP_VERSION` environment variable (do **not** leave a legacy value like `0.x.y` in `.env` — remove the line so the default in `settings.py` takes effect)

---

## Project Structure & Architecture

### Architecture Overview

```mermaid
graph TB
    Browser[Browser] --> Django[Django / Gunicorn :8000]
    Django --> PG[(PostgreSQL :5432)]
    Django --> SMTP[Gmail SMTP]
    Django --> OAuth[Google OAuth]

    subgraph "Django Apps"
        Core["<b>core</b><br/>Dashboard, Auth<br/>Schedule, Utilities<br/><i>4 models</i>"]
        Students["<b>students</b><br/>Student, Parent<br/>Teacher, Group<br/><i>5 models</i>"]
        Billing["<b>billing</b><br/>Payment, Enrollment<br/>Pricing, Exports<br/><i>4 models, 3 services</i>"]
        Comms["<b>comms</b><br/>Email Service<br/>Tasks, Commands<br/><i>0 models</i>"]
    end

    Core --> Students
    Core --> Billing
    Core --> Comms
    Billing --> Students
    Comms --> Students
    Comms --> Billing
```

### App Dependency Flow

```mermaid
graph LR
    students["<b>students</b><br/>(foundation — no dependencies)"] --> billing["<b>billing</b><br/>(FK to Student, Parent)"]
    students --> core["<b>core</b><br/>(FK to Student, Group)"]
    students --> comms["<b>comms</b><br/>(email recipients)"]
    billing --> comms
```

### Directory Layout

```text
five-a-day/
├── project/
│   ├── project/                  Django settings module
│   │   ├── settings.py           Main settings
│   │   ├── settings_test.py      Test overrides (PostgreSQL or SQLite)
│   │   ├── urls.py               Root URL conf → includes 4 app URL files
│   │   ├── celery.py             Celery configuration
│   │   └── wsgi.py / asgi.py
│   │
│   ├── core/                     Dashboard, Auth, Schedule, Utilities
│   │   ├── models.py             TodoItem, HistoryLog, FunFridayAttendance, ScheduleSlot
│   │   ├── views/                13 view modules (dashboard, auth, students, parents,
│   │   │                         payments, management, app_forms, schedule,
│   │   │                         fun_friday_attendance, todos, support, errors,
│   │   │                         testing_tools)
│   │   ├── constants.py          DIAS_ES, MESES_ES, SCHEDULED_APPS
│   │   ├── middleware.py         SimpleAuthMiddleware, QAErrorEmailMiddleware
│   │   ├── decorators.py         qa_access_required (testing env gate)
│   │   ├── context_processors.py Notifications injected into all templates
│   │   ├── transactions.py       Optimized queryset builders
│   │   ├── templates/            ALL HTML templates (base, pages, emails)
│   │   └── static/               CSS (app.css) + JS (13 modules) + images
│   │
│   ├── students/                 People Management
│   │   ├── models.py             Student, Parent, StudentParent, Teacher, Group
│   │   ├── forms.py              StudentForm, ParentForm, ParentFormSet
│   │   ├── admin.py              Custom admin with inlines
│   │   └── urls.py               12 URL patterns
│   │
│   ├── billing/                  Financial Management
│   │   ├── models.py             SiteConfiguration, EnrollmentType, Enrollment, Payment
│   │   ├── forms.py              EnrollmentForm (delegates to service)
│   │   ├── constants.py          Pricing seeds, choice tuples
│   │   ├── services/             EnrollmentService, PaymentService, PricingService
│   │   ├── exports.py            Excel/CSV builders
│   │   ├── admin.py              Payment + Enrollment admin with actions
│   │   ├── urls.py               20 URL patterns
│   │   └── management/commands/  generate_payments, seed_testdata
│   │
│   ├── comms/                    Communications
│   │   ├── services/             EmailService + 12 email functions + PDF gen
│   │   ├── tasks.py              6 Celery tasks
│   │   ├── urls.py               10 URL patterns
│   │   └── management/commands/  send_email, test_all_emails
│   │
│   ├── tests/                    pytest suite (283 tests, 70 % coverage)
│   └── conftest.py               Shared fixtures (models + authenticated_client)
│
├── .github/                      CI/CD — see docs/GITHUB.md
│   ├── workflows/
│   │   ├── ci.yml                Lint + typecheck + tests on every push/PR
│   │   ├── auto-merge.yml        Hourly development → testing merge + PR to main
│   │   ├── codeql.yml            Weekly Python security scan
│   │   └── notify-production.yml Email on push to main
│   ├── dependabot.yml            Weekly dependency updates
│   └── CODEOWNERS                Auto-request reviews from owner accounts
│
├── docs/
│   ├── GITHUB.md                 Full CI/CD + branch protection reference
│   ├── HTTPS.md                  HTTPS setup (Docker Nginx + Cloud Run)
│   ├── UV.md                     UV dependency management guide
│   ├── CELERY.md                 Celery worker/beat reference
│   └── TODO.md                   Open tasks
│
├── scripts/                      Dev helpers (docker_smoke_test, etc.)
├── backups/                      DB dumps from `make backup` (gitignored)
│
├── Dockerfile                    Multi-stage build (builder + runtime)
├── docker-compose.yml            PostgreSQL + Redis + Django + Celery worker + beat
├── docker-compose.testing.yml    QA override (Gunicorn, DEBUG=False)
├── Makefile                      60+ commands (`make help`)
├── pyproject.toml                Dependencies (uv-managed) + tool config
├── uv.lock                       Reproducible dependency lock
├── entrypoint.sh                 Docker entrypoint (migrate, collectstatic, start)
├── .env / .env.testing           Gitignored — never committed
├── CLAUDE.md                     AI development context (project rules)
├── DEPLOYMENT.md                 GCP deployment guide (all 3 environments)
└── README.md                     This file
```

### App: core

Dashboard, authentication, scheduling, and shared utilities. Owns all views and templates.

| Component | Details |
|-----------|---------|
| **Models** | TodoItem, HistoryLog (1000-entry cap), FunFridayAttendance, ScheduleSlot |
| **Views** | 13 modules: auth, dashboard, students, parents, payments, management, app_forms, schedule, fun_friday_attendance, todos, support, errors, testing_tools |
| **Middleware** | SimpleAuthMiddleware — session-based, protects all routes except /login/, /health/, /static/ |
| **Templates** | base.html (layout), 15+ page templates, 12 email templates, error pages |
| **Static** | app.css (sidebar/icons), 13 JS modules, logo |

See [core/README.md](project/core/README.md) for details.

### App: students

People management — the foundation app with no external dependencies.

| Component | Details |
|-----------|---------|
| **Models** | Student (with age calc, withdrawal tracking), Parent (DNI unique), Teacher, Group, StudentParent (M2M through) |
| **Forms** | StudentForm (birth_date validation), ParentForm (DNI validation), ParentFormSet |
| **Admin** | StudentAdmin with StudentParentInline, ParentAdmin with ParentStudentInline |
| **URLs** | 12 patterns: CRUD + search + fun friday attendance |

See [students/README.md](project/students/README.md) for details.

### App: billing

Financial management with a dedicated service layer.

| Component | Details |
|-----------|---------|
| **Models** | SiteConfiguration (singleton pricing), EnrollmentType (plan types), Enrollment (with discount flags), Payment (with overdue detection) |
| **Services** | EnrollmentService (creation + discounts), PaymentService (generation + calculations), PricingService (centralized config access) |
| **Constants** | Pricing seeds, ENROLLMENT_TYPE_CHOICES, SCHEDULE_TYPE_CHOICES, PAYMENT_METHOD_CHOICES, etc. |
| **Exports** | build_database_workbook() → multi-sheet .xlsx |
| **Commands** | `generate_payments --month X --year Y [--dry-run]` |
| **URLs** | 20 patterns: payment CRUD, enrollment API, management, exports |

See [billing/README.md](project/billing/README.md) for details.

### App: comms

Email communications — no database models, pure service layer.

| Component | Details |
|-----------|---------|
| **EmailService** | Generic HTML email sender with inline images and attachments |
| **Email functions** | 12 convenience functions (birthday, welcome, enrollment, payment reminder, receipts, tax cert, etc.) |
| **Celery tasks** | 6 tasks with retry logic: welcome, birthday (single + batch), payment reminders, generic, enrollment confirmation |
| **Commands** | `send_email --template X [--test]`, `test_all_emails [--only X,Y]` |
| **URLs** | 10 patterns: all email app form views |

See [comms/README.md](project/comms/README.md) for details.

### Design Decisions

| Decision | Rationale |
|----------|-----------|
| Views stay in core | Models split across apps, but all views in `core/views/` avoids template/URL fragmentation. Each app's `urls.py` imports from core. |
| Service layer in billing | Business logic (pricing, discounts, payment generation) extracted from forms/views into testable services. |
| SiteConfiguration singleton | All pricing editable from UI. Auto-creates with defaults. No hardcoded prices in views. |
| Session-based auth | SimpleAuthMiddleware with env var credentials. Sufficient for 3-10 users until v1.6. |
| Tailwind CDN | Zero build tools. All utilities available instantly. Custom violet palette in config block. |
| PostgreSQL everywhere | Same database engine in development, testing, and production. Avoids SQLite behavioral differences. |

---

## Features by View

### Home (Dashboard)

The main landing page. Shows real-time operational data for the current month.

- **Pending payments card** — count + student names with amounts. Click count to expand modal with full student list and individual amounts.
- **Birthdays card** — monthly count with today's birthdays highlighted by name.
- **Upcoming events** — Fun Fridays and scheduled email sends for the rest of the month, linked to their form views.
- **Monthly revenue** — expected total (all due this month) vs completed total (paid this month), with payment count.
- **Todo list** — create tasks with date selector (today / this week's Friday / custom date picker). Overdue items shown in red. Check to complete (deletes + logs to HistoryLog). Sorted by due date.
- **History dropdown** — lazy-loaded, paginated (20 per page) log of all actions: payments completed, students enrolled, emails sent, config changes.
- **Notification bell** — badge count of today's due tasks + today's scheduled email sends.

### Students

Student management with toolbar, inline actions, and real-time filtering.

- **Student table** — columns: name, group (color badge), enrollment type, Fun Friday status icon. Rows have `data-*` attributes for client-side filtering.
- **Search** — real-time filter by name (client-side, no server round-trip).
- **Sort** — 4-state cycle: date ascending → date descending → name A-Z → name Z-A.
- **Fun Friday toggle** — per-row button. States: green check (registered this week), amber check (this + last week), amber X (only last week), grey X (neither). AJAX POST to `/api/students/{id}/fun-friday/toggle/`.
- **Fun Friday filter** — 3-state cycle: all → not this week → this week only.
- **Type filter** — 4-state cycle: all → children only → adults only → language cheque students.
- **New student dropdown** — choose creation flow: new parent → new student, existing parent → new student, or adult student (no parent).

### Student Create

Multi-step creation form with live price calculator.

- **Parent selection** — either create new (name, DNI, phone, email, IBAN) or search existing parents with pagination (6 per page).
- **Student fields** — first name, last name, birth date (validated: not future), school, allergies, GDPR consent, group selector.
- **Enrollment plan** — dropdown: monthly full-time (2 days/week), monthly part-time (1 day/week), quarterly. Checkboxes: language cheque discount, sibling discount (with sibling search), special/manual price.
- **Live price calculator** — updates as you change plan/discounts. Shows base price, strikethrough, final price, and breakdown text (e.g., "trimestral incl. -5%, -20 cheque").
- **Adult mode** — no parent needed, email/phone on student, fixed adult_group pricing.
- **On submit** — atomic transaction creates: Student → StudentParent link → Enrollment (active) → Payment (enrollment fee, pending) → HistoryLog entry → Celery welcome email task.
- **Success page** — shows student name, enrollment fee amount. Auto-redirects to student list after 4 seconds. Option to "create sibling" (pre-fills same parent).

### Student Detail & Update

- **Detail view** — personal info, linked parents with contact details, enrollment history (all enrollments, active highlighted), payment history, Fun Friday dates with add/remove.
- **Enrollment modality toggle** — switch monthly ↔ quarterly via AJAX.
- **Update view** — same form as create, pre-filled. Saves student changes + finishes old enrollment + creates new enrollment.

### Payments

Payment management with search, filtering, pagination, and quick-complete.

- **Stats bar** — 4 cards: expected total, completed total, pending total, overdue total. All for the current period.
- **Payment table** — columns: student, parent, concept, amount, method, status badge, due date, payment date. Client-side pagination (10 per page).
- **Search** — real-time filter by student name, parent name, concept, or reference number.
- **Status filter** — 4-state cycle: all → pending → completed → overdue.
- **Type filter** — 5-state: all → enrollment → monthly → quarterly → other.
- **Quick complete** — click a pending status badge → dropdown with 3 payment methods (cash / transfer / card) → one click marks as completed with today's date, logs to history.
- **Create payment** — autocomplete student search → autocomplete parent search → validates student-parent relationship → select type, method, amount, dates, concept.
- **Detail view** — read-only display of all payment fields.
- **Export** — CSV download (all payments) and Excel download (full database: students + enrollments + payments as multi-sheet .xlsx).

### Schedule

Weekly class timetable with drag-and-drop group assignment.

- **Grid** — 5 columns (Mon-Fri) × 3 time rows × 2 sub-columns. Time slots: 16:10-17:30, 17:40-19:00, 19:10-20:30. Friday: 16:00-17:20.
- **Edit mode** — toggle button. In edit mode, click any cell → dropdown to assign a group. Saves via AJAX to `/api/schedule/slot/save/`.
- **Cell display** — group color, group name, teacher first name, student first names.

### Fun Friday

Dedicated attendance management for the weekly Fun Friday event.

- **Student list** — all non-adult active students, grouped by class group.
- **Toggle buttons** — same icon system as student list. AJAX toggles.
- **This week / Last week panels** — lists of registered students for each Friday.
- **Search, sort, filter** — same tools as student list.

### Apps (Email Tools)

Hub page listing all 10 email communication tools. Each follows a consistent pattern:

1. **Form** — fields specific to the email type (dates, activity description, year, etc.)
2. **Email preview** — collapsible panel showing the rendered email HTML. "Refresh" button fetches live preview with current form data via AJAX.
3. **Test send** — sends to `EMAIL_TEST_1` / `EMAIL_TEST_2` env vars for verification before bulk send.
4. **Send** — iterates over qualifying parent emails, sends individually, counts success/failures, logs to HistoryLog, shows flash messages.

| App | Email Template | Recipients | Trigger |
|-----|---------------|------------|---------|
| Fun Friday | `fun_friday.html` | Parents with active non-adult students | Weekly, manual |
| Payment Reminder | `payment_reminder.html` | Parents with active students | Monthly, manual |
| Vacation Closure | `vacation_closure.html` | All parents | Manual |
| Tax Certificate | `tax_certificate.html` | Parents with completed payments in year | Yearly (April) |
| Monthly Report | `monthly_report.html` | All parents (personalized per parent) | Monthly, manual |
| Birthday | `happy_birthday.html` | Parents of today's birthday students | Daily, manual |
| Receipts (child) | `receipt_quarterly_child.html` | Parents with active children | Quarterly, manual |
| Receipts (adult) | `receipt_adult.html` | Adult students | Monthly, manual |
| Welcome | `welcome_student.html` | Parent of new student | On creation (auto) |
| Enrollment | `enrollment_child.html` / `enrollment_adult.html` | Parent of enrolled student | On enrollment |

### Management

Admin configuration panel with live editing.

- **Pricing config** — all fees and discounts from SiteConfiguration. Toggle edit mode → modify values → save via AJAX. Fields: children/adult enrollment fees, full-time/part-time/adult monthly fees, 8 discount types.
- **Teachers** — create via modal (name, email, phone, admin flag). Validates unique email. Lists active teachers.
- **Groups** — create via modal (name, color picker, teacher dropdown). Teacher list populated via AJAX from `/api/teachers/`. Validates unique name.
- **Language cheque API** — `GET /api/students/language-cheque/` returns all students with active language cheque for government reporting.

### Database (All Info)

Paginated read-only tables of all data.

- **Students tab** — sortable by creation date, ID, first name, last name. Paginated (20 per page).
- **Payments tab** — sortable by creation date or student name. Paginated (20 per page).
- **Excel export button** — downloads complete database as `five_a_day_YYYYMMDD.xlsx`.

### Login

Standalone page with custom styling (does not extend base.html).

- **Credentials login** — username/password from `LOGIN_USERNAME` / `LOGIN_PASSWORD` env vars.
- **Google OAuth** — optional. Button shown if `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are configured. Validates email matches `GOOGLE_ALLOWED_EMAIL`. Stores Google credentials in session for Gmail/Sheets API access.
- **Session** — sets `is_authenticated=True` and `username` in Django session. 24-hour expiry.

---

## Testing

### Testing Overview

| Metric | Value |
|--------|-------|
| **Total tests** | 283 |
| **Test files** | 19 |
| **Coverage** | 70% (with `--cov-report=term-missing` on every run) |
| **Runtime** | ~30 seconds (8 parallel workers via pytest-xdist) |
| **Database** | PostgreSQL (same as production) — **always use `make test`** |
| **Framework** | pytest 9 + pytest-django + pytest-cov + pytest-xdist + pytest-randomly |
| **Type checking** | mypy + django-stubs (pre-commit hook) |
| **Security** | bandit security linter (pre-commit hook) |
| **Dependency audit** | pip-audit for CVE scanning |
| **Linting** | Ruff (check + format) via pre-commit hooks |
| **Settings** | `project/settings_test.py` |
| **Fixtures** | `conftest.py` — 15 shared fixtures |

```bash
make test              # Inside Docker (PostgreSQL, parallel, with coverage)
make test-local        # Local against Docker PostgreSQL
make test-sqlite       # Local with SQLite (no Docker)
make test-coverage     # Generate HTML coverage report
make test-fast         # Stop on first failure
make test-k K=payment  # Run tests matching keyword
```

### Model Tests

41 tests in `test_models.py` covering model logic, properties, and database constraints.

| Group | Count | Coverage |
|-------|-------|----------|
| Academic year helpers | 5 | `current_academic_year()` for both semesters, `academic_year_start_date`, `academic_year_end_date` |
| SiteConfiguration | 4 | Singleton creation, pk=1 enforcement, delete prevention, default values |
| Student & Parent | 6 | Properties (`full_name`, `age`), string representation, M2M relationship, DNI uniqueness |
| Student gender | 2 | Default gender value, gender choices |
| Teacher & Group | 4 | Properties, FK relationship, name uniqueness |
| Enrollment | 5 | Properties (`is_paid`, `remaining_amount`), string representation, unique active constraint |
| Cancelled enrollment | 1 | Cancelled enrollment status |
| Inactive student | 1 | Inactive student exists |
| Payment | 4 | `is_overdue` detection (past/future/completed), `clean()` auto-sets payment_date |
| TodoItem & HistoryLog | 5 | `is_overdue`, log creation, 1000-entry cap, debounced logging |
| FunFridayAttendance | 1 | Unique (student, date) constraint |
| ScheduleSlot | 3 | Slot creation, unique (row, day, col) constraint, null group |

### Service Tests

26 tests in `test_services.py` covering business logic in the service layer.

| Group | Count | Coverage |
|-------|-------|----------|
| PricingService | 7 | Monthly fees by schedule type, enrollment fees by student type, quarterly price calculation |
| EnrollmentService | 9 | All enrollment plans (monthly full/part, quarterly), all discount types (sibling, language cheque, both), special pricing, adult enrollment, minimum amount floor (0.01) |
| EnrollmentService errors | 2 | Missing enrollment type validation, payment statistics |
| PaymentService | 8 | Monthly/quarterly amount calculations with all discount combos, June bonus, payment completion, academic month/quarter validation |

### View Tests

65 tests in `test_views.py` covering HTTP responses, AJAX APIs, and user flows.

| Group | Count | Coverage |
|-------|-------|----------|
| Authentication | 6 | Unauthenticated redirect, login page, health check, valid/invalid login, logout |
| Dashboard | 2 | Dashboard, all_info |
| Student views | 4 | Student list, detail, create page, search API |
| Parent views | 2 | Parent create page, search API |
| Payment views | 9 | Payments list, create page, detail, quick-complete (valid + invalid), statistics, CSV export, student-parent validation |
| Payment CRUD | 5 | Delete, deactivate, update JSON, get details API, search |
| Todo & History API | 5 | Todo create/complete/empty text, history list + pagination |
| Management | 6 | Management page, config update, teacher create (+ duplicate), group create, teachers API |
| Email forms | 10 | Apps page, all 8 form pages load + welcome redirect (parametrized) |
| Enrollment API | 3 | Modality update (valid + invalid), language cheque endpoint |
| Error pages | 5 | All 5 error pages render with correct status codes (parametrized) |
| Schedule | 2 | Schedule page, Fun Friday page |
| Fun Friday | 4 | Toggle (valid + adult rejected), add attendance, remove attendance |
| Support | 2 | Missing message validation, no email configuration |

### Additional Test Files (v1.0.0+)

| File | Count | Coverage |
|------|-------|----------|
| `test_constants.py` | 9 | Pure functions: `calculate_discount`, `get_monthly_fee_by_schedule`, `get_enrollment_fee` |
| `test_transactions.py` | 10 | Query helpers: `get_active_students`, `get_payments_for_last_two_school_years`, `get_all_payments_unrestricted` |
| `test_forms.py` | 9 | `EnrollmentForm` validation + `create_enrollment()` delegation to service layer |
| `test_exports.py` | 7 | Excel workbook generation: students, enrollments, payments sheets + combined workbook |
| `test_schedule_views.py` | 8 | Schedule page, save slot (assign + clear + reject GET), Fun Friday (loads, excludes adults) |
| `test_auth_views.py` | 8 | Login (render, redirect, valid/invalid creds, missing env), logout, OAuth redirect |
| `test_student_views.py` | 12 | Student list (search, exclude inactive), detail, create (form, success, adult mode, full POST), search |
| `test_payment_views.py` | 9 | `parse_date_value` (6 formats), payments list, search, quick complete |
| `test_app_form_views.py` | 27 | All email form GET pages, POST preview (JSON), POST send, test_send without env vars |
| `test_parent_views.py` | 4 | ParentCreateView: GET, POST (new + existing DNI + invalid) |
| `test_create_payment_views.py` | 7 | Create payment (form + invalid parent), payment detail, update payment, Excel export |
| `test_student_forms.py` | 7 | StudentForm + ParentForm validation: dates, DNI, required fields |
| `test_context_processors.py` | 11 | Context keys, todo filtering, scheduled apps, history count, support email |
| `test_middleware.py` | 9 | Public/protected paths, session handling |
| `test_email_service.py` | 12 | EmailService: send, recipients, CC/BCC, attachments, fail_silently, bulk |
| `test_email_functions.py` | 10 | All convenience email functions: template, subject, context, fail_silently |

---

## Migrations

All migrations were regenerated from scratch during the v1.0.0 multi-app split.

| App | Migration | Changes | Depends On |
|-----|-----------|---------|------------|
| `students` | `0001_initial` | Teacher, Group, Parent, Student, StudentParent | — |
| `students` | `0002` | Student gender field, StudentParent UniqueConstraint | `students.0001` |
| `billing` | `0001_initial` | SiteConfiguration, EnrollmentType, Enrollment, Payment | `students.0001` |
| `billing` | `0002` | Enrollment academic_year index | `billing.0001`, `students.0002` |
| `core` | `0001_initial` | TodoItem, HistoryLog, FunFridayAttendance, ScheduleSlot | `students.0001` |
| `core` | `0002` | UniqueConstraint for FunFridayAttendance and ScheduleSlot (replaces unique_together) | `core.0001`, `students.0002` |
| `comms` | — | (no models) | — |

```bash
# After modifying models:
make makemigrations   # Creates migrations for all 4 apps
make migrate          # Applies them
```

---

## Security

This section documents every security decision, mechanism, and configuration in the project.

### Authentication

**Mechanism**: Custom session-based authentication with two backends — environment credentials and Google OAuth 2.0.

| Component | File | How it works |
|-----------|------|-------------|
| Login view | `core/views/auth.py` | Validates username/password against `LOGIN_USERNAME`/`LOGIN_PASSWORD` env vars. Sets `request.session["is_authenticated"] = True`. No hardcoded fallbacks — if env vars are missing, login is refused with an error message. |
| Google OAuth | `core/views/auth.py` | Full OAuth 2.0 code flow via `google-auth-oauthlib`. State token stored in session and verified on callback. ID token verified server-side via Google's public keys. Only the email matching `GOOGLE_ALLOWED_EMAIL` (or `EMAIL_HOST_USER` / `DJANGO_SUPERUSER_EMAIL`) is authorized. |
| Auth middleware | `core/middleware.py` | `SimpleAuthMiddleware` protects all routes. Public URLs use exact match for `/login/` and prefix match for `/health/`, `/static/`, `/media/`, `/auth/google/` (covers `/callback/`). All other paths require `session["is_authenticated"]`. |
| OAuth credentials | `core/views/auth.py` | Google tokens (access, refresh) are stored in session server-side. `client_secret` is never sent to the frontend. Allowed email check is backend-only. |

**Design decisions**:
- No Django User model — the system has 3-10 trusted admin users, so session-based auth with env var credentials is simpler and sufficient.
- Google OAuth is optional — if `GOOGLE_CLIENT_ID`/`GOOGLE_CLIENT_SECRET` are not set, the OAuth button is hidden.
- `OAUTHLIB_INSECURE_TRANSPORT` is only set when `DEBUG=True` (for local HTTP testing).

### Session & Cookie Configuration

All cookie flags are enforced via `settings.py` with environment-aware defaults:

| Setting | Development | Production | Purpose |
|---------|------------|------------|---------|
| `SESSION_COOKIE_AGE` | 86400 (24h) | 86400 (24h) | Session lifetime |
| `SESSION_COOKIE_HTTPONLY` | `True` | `True` | Prevents JavaScript access to session cookie |
| `SESSION_COOKIE_SAMESITE` | `Lax` | `Strict` | Prevents cross-site request forgery via session cookies |
| `SESSION_COOKIE_SECURE` | `False` | `True` | Requires HTTPS for cookie transmission |
| `CSRF_COOKIE_HTTPONLY` | `False` | `True` | Prevents JavaScript access to CSRF cookie in production |
| `CSRF_COOKIE_SAMESITE` | `Lax` | `Strict` | Prevents cross-site CSRF cookie leakage |
| `CSRF_COOKIE_SECURE` | `False` | `True` | Requires HTTPS for CSRF cookie |

Production defaults are applied automatically when `DEBUG=False` — no manual override needed in env vars.

### CSRF Protection

- Django's `CsrfViewMiddleware` is active in the middleware stack.
- All POST endpoints receive CSRF validation. JavaScript AJAX requests use `getCsrfToken()` (reads from cookies) and send via `X-CSRFToken` header.
- `CSRF_TRUSTED_ORIGINS` is configured per deployment via the `CSRF_TRUSTED_ORIGINS` env var (see [DEPLOYMENT.md](DEPLOYMENT.md)).
- Only exception: `@csrf_exempt` on `/health/` endpoint (GET-only, returns `{"status": "healthy"}`).

### Transport Security (HTTPS)

When `DEBUG=False`, the following are enforced via `settings.py`:

| Setting | Value | Effect |
|---------|-------|--------|
| `SECURE_SSL_REDIRECT` | `True` | All HTTP requests redirected to HTTPS |
| `SECURE_HSTS_SECONDS` | `31536000` (1 year) | Browser remembers to use HTTPS |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` | HSTS applies to all subdomains |
| `SECURE_HSTS_PRELOAD` | `True` | Eligible for browser HSTS preload lists |

All settings are environment-controlled and only activate when `DEBUG=False`.

### Security Headers

| Header | Setting | Value | Effect |
|--------|---------|-------|--------|
| `X-Frame-Options` | `X_FRAME_OPTIONS` | `DENY` | Prevents clickjacking — page cannot be embedded in iframes |
| `X-Content-Type-Options` | `SECURE_CONTENT_TYPE_NOSNIFF` | `True` | Prevents MIME type sniffing attacks |
| `X-XSS-Protection` | `SECURE_BROWSER_XSS_FILTER` | `True` | Enables browser XSS filter (legacy, supplementary) |

### Infrastructure & Deployment

#### Docker

| Decision | Implementation |
|----------|---------------|
| Non-root container | `Dockerfile` creates user `django` (uid 1000) and runs as `USER django` |
| Multi-stage build | Builder stage compiles dependencies; runtime stage uses `python:3.12-slim` without build tools |
| No secrets in image | `.dockerignore` excludes `.env*`, `scripts/`, `.git/` |
| DB port restricted | `docker-compose.yml` binds PostgreSQL to `127.0.0.1:5432` only (not exposed to network) |
| Health checks | Database has auth-checking healthcheck; web service uses `/health/` endpoint |
| Seed script guard | `scripts/reset_seed_dev_data.py` aborts if `DJANGO_ENV=production` or `DEBUG=False` |

#### Google Cloud Run

Full deployment walkthrough in [DEPLOYMENT.md](DEPLOYMENT.md). Security-relevant decisions:

| Decision | Implementation |
|----------|---------------|
| Secret Manager | All credentials (`DJANGO_SECRET_KEY`, `LOGIN_*`, `EMAIL_SECRET`, `POSTGRES_*`, `GOOGLE_*`) injected at startup from GCP Secret Manager |
| Cloud SQL Auth Proxy | PostgreSQL connection goes through the proxy — no public IP on the database |
| Autoscaling | min=0 (cold starts acceptable) or min=1 (~$7/mo) for always-warm, max=2 instances |
| Probes | Startup probe + liveness probe on `/health/` |
| TLS | Managed automatically by Cloud Run (custom domain + Google-managed certificate) |
| SSL enforced | `SECURE_SSL_REDIRECT=True`, all cookie secure flags enabled when `DEBUG=False` |
| Strict cookies | `SESSION_COOKIE_SAMESITE=Strict`, `CSRF_COOKIE_SAMESITE=Strict`, `CSRF_COOKIE_HTTPONLY=True` |

### Secrets Management

| Rule | Implementation |
|------|---------------|
| No hardcoded credentials | `auth.py` requires `LOGIN_USERNAME`/`LOGIN_PASSWORD` env vars — refuses login if missing |
| No secrets in YAML | Production credentials live in GCP Secret Manager, injected into Cloud Run at startup — never in the repo |
| No secrets in GitHub Actions for deploy | CI uses only non-production Gmail SMTP + Codecov upload token. Production deploy runs manually with the operator's `gcloud` credentials |
| No secrets in Docker image | `.dockerignore` excludes all `.env*` files |
| `.gitignore` coverage | `.env*` pattern excludes all env file variants |
| Production startup validation | `settings.py` raises `ValueError` if `SECRET_KEY` is the dev default and `DEBUG=False` |

### Email Security

| Decision | Implementation |
|----------|---------------|
| TLS enforced | `EMAIL_USE_TLS=True`, port 587 (STARTTLS) |
| App Password | Uses Gmail App Password (not account password) via `EMAIL_SECRET` env var |
| `fail_silently` | Defaults to `False` for single sends (raises on failure); `True` for bulk sends (logs failures) |
| No PII in logs | Celery tasks log by ID (`student_id=X`) not by name/email/DNI |
| Template auto-escaping | All email templates use Django's default auto-escaping — `{{ variable }}` is HTML-safe |
| Inline images | Attached via MIME `Content-ID` headers, not external URLs |

### Data Protection & Input Validation

| Layer | Mechanism |
|-------|-----------|
| **Models** | `DecimalField` with `MinValueValidator` for all money fields. `UniqueConstraint` for enrollment/schedule/attendance integrity. `PROTECT` on foreign keys prevents orphaned records. |
| **Forms** | Django `ModelForm` with `clean_*()` validators. Date fields accept `%Y-%m-%d` and `%d/%m/%Y`. DNI validated for minimum length. |
| **Views** | `get_object_or_404` for safe lookups. `@require_http_methods` on all AJAX endpoints. `Decimal(str(...))` for safe numeric conversion. `json.JSONDecodeError` caught explicitly. |
| **Services** | `transaction.atomic()` wraps multi-model writes (enrollment creation, payment completion). `ValueError` raised for missing config. |
| **GDPR** | `gdpr_signed` field on Student. No student data exposed without authentication. PII removed from log messages. |

### Logging & Monitoring

- Console logging via `StreamHandler` with configurable `LOG_LEVEL` env var.
- Separate loggers for `django` framework and project modules.
- `HistoryLog` model tracks user actions (payment completed, student enrolled, config updated) — capped at 1000 entries with automatic cleanup.
- Celery tasks log by entity ID, not PII.

### Future Security Improvements

These are not blockers but would strengthen the system for scale or compliance:

| Priority | Improvement | Why |
|----------|------------|-----|
| **High** | Rate limiting on login (`django-ratelimit`, 5 attempts/15 min per IP) | Prevents brute force. Currently no protection. |
| **High** | Content-Security-Policy header | Prevents XSS. Currently absent — Tailwind CDN requires `unsafe-inline` for styles, but scripts can be locked down. |
| **High** | Referrer-Policy header (`strict-origin-when-cross-origin`) | Prevents referrer leakage to external links. Currently absent. |
| **Medium** | Session rotation on OAuth login (`request.session.create()`) | Prevents session fixation. Currently session ID persists through OAuth flow. |
| **Medium** | Inactivity timeout (30 min idle logout) | 24h session is long for sensitive student data. |
| **Medium** | Security event audit log (failed logins with IP, CSRF failures) | Currently no visibility into attack attempts. |
| **Medium** | Permissions-Policy header | Disables camera, microphone, geolocation APIs the app doesn't need. |
| **Medium** | `Argon2` password hasher (if Django User model is ever adopted) | Stronger than default PBKDF2. |
| **Low** | Request ID tracking (`X-Request-ID` middleware) | Enables log correlation across services. |
| **Low** | `detect-secrets` pre-commit hook | Prevents accidental secret commits in the future. |
| **Low** | Migrate to OAuth-only (deprecate password login) | Reduces credential attack surface to zero. |
| **Low** | Web Application Firewall (WAF) rules at cloud provider level | Blocks common attack patterns before they reach Django. |

---

## Testing Environment (QA)

> **This section is for testers, teachers, and anyone helping us try out the application before it goes live.**
> You do not need to be a programmer to use the testing environment. If something looks wrong or confusing, that is exactly the kind of feedback we need.

### What is the testing environment?

The testing environment is a copy of the real application that runs on the internet, just like the final version will. It looks and works exactly the same, but it uses **fake data** — fake students, fake parents, fake payments. Nothing you do here affects real people or real money.

Think of it as a **rehearsal stage**: you can click anything, try any feature, and even break things. We can always reset it.

### How to access it

| | |
|---|---|
| **Web address** | *(will be provided once deployed on GCP)* |
| **Username** | See `.env.testing` → `LOGIN_USERNAME` |
| **Password** | See `.env.testing` → `LOGIN_PASSWORD` |

The login credentials are stored in the `.env.testing` file and are **never committed to the repository**. Ask the development team if you need them.

1. Open the web address in your browser (Chrome, Firefox, Safari, or Edge all work).
2. You will see a login page. Type the username and password you were given.
3. After logging in you will see the **Dashboard** — the home screen with today's tasks, pending payments, and birthdays.

### What you can test

Here is a quick checklist of things to try. If anything does not work, take note of what happened and tell the development team.

- **Dashboard** — Does it load? Do the numbers make sense?
- **Students** — Can you see the list of students? Open a student's profile? Search by name?
- **Create a student** — Fill in the form and save. Does the new student appear in the list?
- **Payments** — Open the payments page. Try marking a payment as completed. Try filtering by status.
- **Schedule** — Open the weekly schedule. Can you see groups assigned to time slots?
- **Fun Friday** — Toggle a student's attendance on or off.
- **Email forms** (Apps section) — Open each email form. You do not need to send real emails; just verify the forms load correctly.
- **Management** — Can you update the site configuration (pricing)? Create a teacher or group?
- **General navigation** — Does the sidebar work? Do all links go to the right page? Is the text readable?
- **Testing Tools** (the blue "info" icon at the bottom of the sidebar) — This is your QA control panel:
  - **Project Info** — shows the current software version, last commit, server status
  - **Error Reporting toggle** — turn this ON so every server error is automatically emailed to the development team with full details
  - **Database Seeding** — click to populate the database with test data, or wipe and start fresh
  - **QA Backlog** — report bugs and suggestions directly from this page; each new task is emailed to the development team

### How to report a problem

When something goes wrong, please note:

1. **What page you were on** — copy the web address from your browser's address bar, or describe the page ("I was on the payments list").
2. **What you did** — "I clicked the green Complete button on a payment" or "I searched for a student named Sofia".
3. **What happened** — "The page showed an error" or "Nothing happened" or "It showed the wrong information".
4. **Screenshot** — If possible, take a screenshot (press the Print Screen key or use the Snipping Tool on Windows).

Send this information to the development team. Even a short message like "The payments page shows an error when I click Export" is helpful.

### Error pages you might see

| Page | What it means |
|------|--------------|
| **Login page** (you are sent back to login) | Your session expired. Just log in again. |
| **Page not found (404)** | You followed a link that does not exist. Go back to the Dashboard. |
| **Server error (500)** | Something broke inside the application. This is a bug — please report it. |
| **Forbidden (403)** | The application blocked your action for security reasons. Try logging in again. |

### For developers: how the QA environment works

The testing environment mirrors production:

| Setting | Value | Why |
|---------|-------|-----|
| `DEBUG` | `False` | Hides technical details from error pages, same as production |
| `DJANGO_ENV` | `testing` | Like production (collectstatic, Gunicorn, secure cookies) but enables the `/testing/` dashboard |
| Server | Gunicorn (2 workers) | Same as production (not Django's development server) |
| HTTPS cookies | `Secure=True`, `SameSite=Strict` | Same cookie policy as production |
| HTTPS | Via Nginx reverse proxy (local) or Cloud Run (GCP) | See [HTTPS.md](docs/HTTPS.md) for full setup guide |
| `SECURE_PROXY_SSL_HEADER` | Trusts `X-Forwarded-Proto` from reverse proxy | Enables Django to detect HTTPS behind Nginx/Cloud Run |
| Database | PostgreSQL 16 (separate volume) | Isolated from the development database |
| Login | Credentials in `.env.testing` | Dedicated QA credentials, never committed to git |
| Admin panel | `/admin/` — credentials in `.env.testing` | Django admin for inspecting raw data |

**Configuration files:**

| File | Purpose |
|------|---------|
| `.env.testing` | All environment variables for QA (credentials, database, security flags) |
| `docker-compose.testing.yml` | Docker override that switches to Gunicorn and uses a separate database volume |
| `seed_testdata` command | Populates the database with realistic fake data |
| `HTTPS.md` | Full guide for HTTPS setup with Docker (Nginx + self-signed cert) and GCP Cloud Run |
| `/testing/` | In-app QA dashboard with project info, seeding, backlog, and error reporting toggle |
| `core/decorators.py` | `qa_access_required` decorator — reusable access gate for QA-only views |

#### Access control for `/testing/`

The testing dashboard and all its API endpoints are protected by three conditions that must **all** be true:

| Condition | Setting | Where it's checked |
|---|---|---|
| Environment is `testing` | `DJANGO_ENV=testing` | `settings.IS_TESTING_ENV` |
| Debug is off | `DJANGO_DEBUG=False` | `settings.IS_TESTING_ENV` |
| User matches QA username | `QA_TESTING_USERNAME` in `.env.testing` | `core/decorators.py` via session |

If any condition fails, the page returns **404 Not Found** (not 403) so the URL appears not to exist. The sidebar icon is also hidden — controlled by the `show_testing_tools` context variable injected by `core/context_processors.py`.

This means:
- In **development** (`DEBUG=True`): the page doesn't exist, no sidebar icon.
- In **production** (`DJANGO_ENV=production`): the page doesn't exist, no sidebar icon.
- In **testing** with a **non-QA user**: the page doesn't exist, no sidebar icon.
- In **testing** with the **QA user** (`manitas`): full access, sidebar icon visible.

The QA username is configured in `.env.testing` (never hardcoded) via `QA_TESTING_USERNAME`. To grant another user access, change the value in the env file.

**Running locally (for developers):**

```bash
# Start the QA environment
make testing-up

# Populate with test data (students, parents, payments, etc.)
make testing-seed

# Wipe everything and re-seed from scratch
make testing-reset

# View logs
make testing-logs

# Stop the environment
make testing-down

# Full rebuild (after code changes)
make testing-rebuild
```

The `seed_testdata` command creates:
- 3 teachers, 5 groups
- 6 parents, 12 child students, 3 adult students, 1 inactive student
- Active enrollments with monthly and quarterly payment plans
- Payments in various states (completed, pending, overdue)
- Schedule slots, todo items, and history log entries

Use `--reset` to wipe and re-seed, or `--small` for a minimal dataset (6 children only).

> **Deploying the QA environment** — see [DEPLOYMENT.md](DEPLOYMENT.md) for the full GCP plan. Testing runs on a Compute Engine e2-micro (free tier) with Docker Compose, while production uses Cloud Run + Cloud SQL.

---

## CI/CD & GitHub Actions

The project runs a fully automated CI/CD pipeline on GitHub Actions. Every push is tested, every merge is audited, and production is reached only through a protected pull request. The full configuration reference is in [docs/GITHUB.md](docs/GITHUB.md) — this section is the overview.

### Pipeline Overview

```text
Push to development
        │
        ▼
CI runs (lint + typecheck + tests) + CodeQL
        │
        │  hourly cron
        ▼
Auto-merge check
  • development ahead of testing?
  • last commit ≥ 24 h old?
  • CI passing on that commit?
  • version bumped in pyproject.toml (dev > testing)?
        │ all yes
        ▼
git merge development → testing
(commit: "YYYY-MM-DD - <last commit message>")
        │
        ├── CI re-runs on testing
        └── PR created: testing → main
        │
        ▼
Email to owners (OWNER_EMAILS)
        │
        ▼
Manual review + Code Owner approval
        │
        ▼
Merge to main (protected — all checks required)
        │
        ▼
Email to hellofiveaday@gmail.com
(production deploy ready)
```

### Branch Strategy

| Branch        | Purpose                                  | Protected                | Direct push              |
|---------------|------------------------------------------|--------------------------|--------------------------|
| `main`        | Production. Every commit is deployable.  | Full protection          | No (PR + review only)    |
| `testing`     | Staging. Auto-merged from development.   | Minimal (no force/delete)| Only from auto-merge flow|
| `development` | Active development. Day-to-day work.     | None                     | Yes                      |

Feature branches off `development` are welcome for non-trivial work, but the expected flow is: work on `development` → wait 24 h → auto-promoted to `testing` → manual merge to `main`.

### Workflows

| Workflow | File | Triggers | Purpose |
|----------|------|----------|---------|
| **CI** | [`ci.yml`](.github/workflows/ci.yml) | Push to `development`/`testing`/`main`; PRs to `testing`/`main` | Three parallel jobs — **Lint** (Ruff + Bandit), **Type check** (mypy), **Tests** (pytest + PostgreSQL 16 service container + Codecov upload) |
| **Auto-merge** | [`auto-merge.yml`](.github/workflows/auto-merge.yml) | Hourly cron + manual dispatch | Merges `development` → `testing` when conditions pass, creates PR to `main`, emails owners |
| **CodeQL** | [`codeql.yml`](.github/workflows/codeql.yml) | Push to `main`/`testing`/`development`; PRs to `main`; Monday 04:30 UTC | Python static security analysis (OWASP Top 10, Django-specific queries) |
| **Notify production** | [`notify-production.yml`](.github/workflows/notify-production.yml) | Push to `main` | Emails `hellofiveaday@gmail.com` with commit info and `gcloud` deploy instructions |
| **Dependabot** | [`dependabot.yml`](.github/dependabot.yml) | Weekly (Mondays 08:00 Madrid) | Grouped Python and GitHub Actions updates targeting `development` |

Concurrent CI runs on the same branch cancel each other automatically — new pushes always produce a fresh run.

### Automated Flows

**1. You push to `development`**

- CI triggers immediately (lint, typecheck, tests run in parallel, ~2-4 min)
- CodeQL triggers immediately (weekly scan also runs independently)
- The hourly auto-merge cron promotes to `testing` only when **all four** conditions hold: dev is ahead of testing, the last commit is ≥ 24 h old, CI is green, **and the version in `pyproject.toml` has been bumped** (strictly higher than `testing`'s version). Without a version bump the merge is skipped even with 24 h of new commits on dev — run `make pc-run` (answer yes) or `make version x.y.z` before the next tick to unlock it.

**2. Auto-merge fires**

- Creates a `--no-ff` merge commit on `testing` titled `YYYY-MM-DD - <your last commit message>`
- Pushes to `testing` (which triggers CI on `testing`)
- **Creates and pushes an annotated staging tag `testing-vX.Y.Z`** on the new testing merge commit
- Opens PR `testing → main` if one is not already open (title matches the merge commit)
- Sends an HTML email to `OWNER_EMAILS` with version bump, staging tag, and a "Review PR" button

**2b. You merge the PR → release tag on main**

- `notify-production.yml` reads `version` from `pyproject.toml` on `main`'s new HEAD
- **Creates and pushes an annotated release tag `vX.Y.Z`** on that commit (skipped if tag already exists)
- Sends an HTML email to `hellofiveaday@gmail.com` with the release tag and `gcloud` deploy steps

The two tag namespaces (`testing-vX.Y.Z` and `vX.Y.Z`) are fully independent — the `testing → main` PR can use any merge strategy (merge commit, squash, or rebase) because the release tag is derived from `pyproject.toml`, not from commit SHA continuity.

**3. You review and merge the PR**

- All required checks must pass (Lint, Type check, Tests, CodeQL alerts, Code Owner approval)
- You cannot approve your own PR — the second owner account approves
- On merge, `main` is updated

**4. Production notification fires**

- `notify-production.yml` sends an email to `hellofiveaday@gmail.com`
- Email contains commit info, file-change summary, and the exact `gcloud` commands to deploy to Cloud Run

### Branch Protection — `main`

Configure at **Settings → Branches → Add ruleset**, target `main`:

**Required status checks** (names must match CI job names exactly):

| Check | Workflow |
|-------|----------|
| `Lint` | ci.yml |
| `Type check` | ci.yml |
| `Tests` | ci.yml |
| `Analyze Python` | codeql.yml |

**Protection rules** (every item below enabled):

| Rule | Setting |
|------|---------|
| Require a pull request before merging | ✓ |
| Required approvals | **1** (higher if you add collaborators) |
| Dismiss stale reviews when new commits are pushed | ✓ |
| Require review from Code Owners | ✓ |
| Require status checks to pass | ✓ |
| Require branches to be up to date before merging | ✓ |
| Require conversation resolution before merging | ✓ |
| Require signed commits | ✓ (strongly recommended for a public repo) |
| Require linear history | ✓ (enforces squash/rebase merges) |
| Restrict who can push to matching branches | ✓ |
| Do not allow bypassing the above settings | ✓ (admins follow the same rules) |
| Allow force pushes | ✗ |
| Allow deletions | ✗ |

### Branch Protection — `testing`

`testing` needs direct pushes from the auto-merge workflow, so PR requirements are **not** enforced. Apply only safety rails:

| Rule | Setting |
|------|---------|
| Require a pull request before merging | ✗ |
| Allow force pushes | ✗ |
| Allow deletions | ✗ |
| Require status checks to pass (optional) | ✓ — lets CI block a broken auto-merge from polluting `testing` further |

### Public Repository Hardening

Because this repository is **public**, extra care is taken to prevent accidental secret leaks, abuse of the CI, and unreviewed contributions:

| Control | Where | Why |
|---------|-------|-----|
| **GitHub Secret Scanning** | Settings → Code security | Free for public repos — detects committed secrets across history |
| **Push Protection** | Settings → Code security | Free for public repos — blocks pushes that contain secrets before they land |
| **CodeQL** | `codeql.yml` + Settings → Code security | Free for public repos — weekly security analysis |
| **Dependabot alerts + security updates** | Settings → Code security | Free for public repos — fixes known CVEs in dependencies |
| **Require 2FA for all contributors** | Organization settings (if in an org) | Prevents compromised account pushes |
| **Restrict fork PRs from running CI with secrets** | Settings → Actions → Fork PR workflows: require approval for first-time contributors | Prevents secret exfiltration via malicious PRs from forks |
| **Actions allow-list** | Settings → Actions → Allow specific actions | Prevents supply-chain attacks — pin to verified creators only |
| **Workflow permissions default: read-only** | Settings → Actions → Workflow permissions | Individual workflows explicitly request `write` where needed |
| **Block workflows from approving PRs** | Settings → Actions → Allow GitHub Actions to create and approve pull requests: **only allow create, not approve** | Humans must approve, even automated PRs |
| **SECURITY.md** | Root of the repo | Public disclosure policy so researchers know how to report vulnerabilities privately |
| **License file** | Root of the repo | Required for a public repo — defines what others can legally do with the code |

The `.env` file is gitignored and **never** committed. Production secrets live in GCP Secret Manager (see [DEPLOYMENT.md](DEPLOYMENT.md)), not in the repository or in GitHub Secrets. GitHub Secrets are used only for CI operations (sending notification emails, uploading coverage).

### Required GitHub Secrets

Configure at **Settings → Secrets and variables → Actions**:

| Secret | Required by | Purpose |
|--------|-------------|---------|
| `GH_PAT` | auto-merge.yml | Fine-grained Personal Access Token. Pushes to `testing` and creates PRs *while triggering downstream CI* (which the default `GITHUB_TOKEN` cannot do). Permissions: Contents RW, Pull requests RW, Checks R, Metadata R |
| `EMAIL_HOST_USER` | auto-merge.yml, notify-production.yml | Gmail address used to send notification emails |
| `EMAIL_SECRET` | auto-merge.yml, notify-production.yml | Gmail App Password — can be the same one the application uses for transactional email |
| `OWNER_EMAILS` | auto-merge.yml | Comma-separated recipient list for the `development → testing` merge notification |
| `CODECOV_TOKEN` | ci.yml | Optional — only needed for private repos. Public repos push coverage anonymously |

**Rotate `GH_PAT` annually.** Without it, the auto-merge falls back to the default `GITHUB_TOKEN`, which cannot trigger CI on PRs it creates — breaking the pipeline silently.

### Email Notifications

| Event | Recipient | Sent by |
|-------|-----------|---------|
| `development → testing` merged + PR opened to `main` | `OWNER_EMAILS` (secret) | auto-merge.yml |
| New commit on `main` (production ready to deploy) | `hellofiveaday@gmail.com` (hardcoded) | notify-production.yml |

Both use Gmail SMTP via the `dawidd6/action-send-mail@v3` action. Emails include HTML formatting, links to the commit/PR, and actionable next steps.

### Dependabot

Dependabot opens **weekly PRs on `development`** (Mondays, 08:00 Europe/Madrid) for:

- **Python packages** — minor and patch updates grouped into a single PR. Django major version bumps are intentionally ignored (require manual upgrade planning).
- **GitHub Actions** — updates to `actions/*`, `astral-sh/setup-uv`, `dawidd6/action-send-mail`, etc.

PRs are labelled `dependencies` + `python` or `github-actions` for easy filtering. The normal 24 h cycle carries merged updates to `testing` and then to `main`.

### CodeQL Security Scanning

Runs on every push and PR to `main`, plus a full scan every Monday at 04:30 UTC. Uses the `security-and-quality` query suite — covers OWASP Top 10, CWE Top 25, and Django-specific queries (SQL injection, path traversal, hardcoded credentials, insecure deserialization, etc.).

Results appear in **Security → Code scanning alerts**. A new alert on `main` does not auto-block future merges unless branch protection is configured to require the CodeQL check.

---

## Contributing

### Development Workflow

```bash
# First-time setup
uv sync --no-install-project   # Install all dependencies (UV — see docs/UV.md)
make pre-commit-install        # Install the git pre-commit hook
make up                        # Start Docker (PostgreSQL + Redis + Django + Celery)
```

1. Work on `development` (or a short-lived branch off `development`)
2. Make changes following the conventions below
3. Run `make pc-run` — Ruff + mypy + bandit all pass, offers to auto-bump the patch version on success, and auto-stages `uv.lock` if regenerated
4. Run `make test` — all 283 tests must pass (PostgreSQL via Docker, parallel, with coverage)
5. `git commit` with a message like `v1.0.6 - Short description` (version comes first — conventions match every other commit in the project)
6. `git push origin development`
7. CI runs automatically on your push (see [CI/CD](#cicd--github-actions))
8. ~24 h later, the auto-merge pipeline promotes your commit to `testing` and opens a PR to `main` for your review

Pre-commit hooks run **Ruff** (lint + format), **mypy** (type checking), and **bandit** (security) automatically on every `git commit`. If a hook modifies files (e.g. mypy regenerates `uv.lock`), the commit aborts — running `make pc-run` once resolves this by staging the regenerated lock file.

### Make Commands (Developer Tooling)

| Tool | Purpose | Command |
|------|---------|---------|
| **UV** | Dependency management | `uv sync`, `uv add`, `uv lock` |
| **Ruff** | Lint + format | `make lint`, `make format` |
| **mypy** | Type checking | `make mypy` |
| **bandit** | Security linting | `make bandit` |
| **pip-audit** | Dependency CVE scanning | `make audit` |
| **pytest-xdist** | Parallel test execution | Built into `make test` (`-n auto`) |
| **pytest-randomly** | Randomized test ordering | Built into `make test` (seed printed) |
| **pytest-cov** | Coverage reporting + badge | `make test`, `make coverage-badge` |
| **pre-commit** | Git hooks: ruff, ruff-format, mypy, bandit | `make pre-commit-install` (first-time), `make pc-run` (dry-run all hooks + auto bump) |
| **make version** | Bump version in both `pyproject.toml` and `settings.py` | `make version x.y.z` (positional, with `y/N` confirmation) |

All tools are configured in `pyproject.toml` and installed as dev dependencies via `uv sync`.

### Code Conventions

| Area | Convention |
|------|-----------|
| **Language** | Code in English, UI/templates in Spanish, comments mixed |
| **Models** | Explicit `db_table`, `created_at`/`updated_at` timestamps, BigAutoField PKs |
| **Views** | CBVs for CRUD, FBVs for everything else. AJAX returns `{"success": bool, ...}` |
| **Forms** | ModelForms for data entry. Business logic delegates to services. |
| **Templates** | Extend `base.html`. Blocks: `title`, `page_title`, `content`, `extra_js` |
| **JS** | External files in `core/static/js/`. Django data via `data-*` attrs or `window.CONFIG` |
| **Services** | Pure business logic in `billing/services/`. No request/response objects. |
| **Tests** | pytest with fixtures in `conftest.py`. `authenticated_client` for view tests. |
| **Imports** | Always explicit — no `from app.models import *` |
| **Pricing** | Always from `SiteConfiguration.get_config()`, never hardcoded |
| **Template names** | Always in English (e.g., `enrollment_child.html`, not `matricula_niño.html`) |

### Adding a Feature

1. **Model** → correct app (students/billing/core), explicit `db_table`
2. **Service** → `billing/services/` or new service if it has business logic
3. **View** → appropriate `core/views/` module, add to `__init__.py` re-exports
4. **URL** → correct app's `urls.py`
5. **Template** → `core/templates/`, extend `base.html`
6. **Tests** → fixtures in `conftest.py`, tests in correct test file
7. **Admin** → correct app's `admin.py`
8. **Docs** → update this README, app README, CLAUDE.md if needed

---

## License

Private project — all rights reserved.

Developed for Five a Day English Academy, Albacete, Spain.
