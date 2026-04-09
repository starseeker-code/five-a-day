# core — Dashboard, Auth, Schedule, Shared Utilities

The `core` app is the "everything else" app — it owns the dashboard, authentication, scheduling, and lightweight cross-cutting models that don't belong to a specific domain.

## Models

| Model | Table | Purpose |
| ----- | ----- | ------- |
| **ScheduleSlot** | `schedule_slots` | Weekly schedule grid (row, day, col) with group FK |
| **FunFridayAttendance** | `fun_friday_attendance` | Tracks student attendance on Fun Fridays |
| **TodoItem** | `todo_items` | Dashboard task list with due dates |
| **HistoryLog** | `history_logs` | Audit trail of user actions (auto-capped at 1,000) |

## Views (core/views/)

The monolithic `views.py` was split into 12 focused modules:

| Module | Views | Description |
| ------ | ----- | ----------- |
| `auth.py` | `login_view`, `logout_view`, `google_oauth_redirect`, `google_oauth_callback` | Session-based auth + Google OAuth |
| `dashboard.py` | `home`, `all_info` | Dashboard with stats, todos, birthdays; database view |
| `schedule.py` | `schedule_view`, `save_schedule_slot`, `fun_friday_view` | Weekly schedule grid + Fun Friday list |
| `fun_friday_attendance.py` | `toggle_fun_friday_this_week`, `add/remove_fun_friday_attendance` | AJAX attendance toggles |
| `todos.py` | `create_todo`, `complete_todo`, `history_list` | Todo CRUD + history pagination API |
| `students.py` | `StudentCreateView`, `StudentListView`, etc. | Student/parent CRUD (CBVs + FBVs) |
| `parents.py` | `ParentCreateView` | Parent creation CBV |
| `payments.py` | `payments_list`, `create_payment`, `quick_complete_payment`, etc. | Payment CRUD + AJAX APIs |
| `management.py` | `gestion_view`, `update_site_config`, `create_teacher`, `create_group` | Admin config panel |
| `app_forms.py` | `fun_friday_form`, `payment_reminder_form`, etc. (10 views) | Email app form views |
| `support.py` | `submit_support_ticket` | Support ticket email API |
| `errors.py` | `handler400-500`, `health_check` | Error pages + health endpoint |

## URL Patterns (core/urls.py)

Routes for: login/logout, dashboard, schedule, todos, history, support, error test pages.

Student, payment, management, and email app routes live in `students/urls.py`, `billing/urls.py`, and `comms/urls.py` respectively, but their views are still in `core/views/`.

## Middleware

**SimpleAuthMiddleware** — session-based auth that protects all URLs except `/login/`, `/health/`, `/static/`, `/media/`, and `/auth/google/`. Credentials come from `LOGIN_USERNAME`/`LOGIN_PASSWORD` env vars.

## Templates

All templates live in `core/templates/`:

- `base.html` — main layout (sidebar, header, support modal, Tailwind CDN config)
- `home.html`, `login.html`, `schedule.html`, `fun_friday.html`, etc.
- `payments/` — payment list, create, detail
- `apps/` — email form views + `_email_preview.html` partial
- `emails/` — 12 HTML email templates extending `emails/base_email.html`
- `400.html` through `500.html` — error pages

## Static Files

- `css/app.css` — sidebar transitions, Material Symbols icon font settings
- `js/base.js` — notification/history dropdowns (loaded on every page)
- `js/support.js` — support ticket modal
- `js/home.js`, `js/students.js`, `js/payments.js`, etc. — per-page modules

## Cross-App Communication

- Imports `Student`, `Parent`, `Group` from **students**
- Imports `Payment`, `Enrollment`, `SiteConfiguration` from **billing**
- Imports `email_service`, email functions from **comms**
- Exports `HistoryLog` used by billing views for audit logging
- Exports `FunFridayAttendance` used by students views
- `constants.py` exports `DIAS_ES`, `MESES_ES`, `SCHEDULED_APPS` used by context processors and views
