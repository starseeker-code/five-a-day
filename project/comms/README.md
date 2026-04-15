# comms — Communications

The `comms` app owns all email sending logic: the EmailService class, 12+ convenience email functions, Celery async tasks, and management commands for sending emails.

**No database models** — all state lives in the other apps. Comms is purely a service layer for communications.

## Services

### EmailService (`comms/services/email_service.py`)

Generic email sending service with HTML template rendering and inline images.

- `send_email(template_name, recipients, subject, context, ...)` — renders a Django template and sends via SMTP
- `send_bulk_emails(template_name, emails_data, ...)` — sends multiple emails with the same template
- `email_service` — singleton instance used throughout the project

Templates live in `core/templates/emails/` and extend `emails/base_email.html`.

### Email Functions (`comms/services/email_functions.py`)

Convenience functions for each email type. Each wraps `email_service.send_email()` with template-specific parameters:

| Function | Template | Trigger |
| -------- | -------- | ------- |
| `send_birthday_email` | `happy_birthday` | Daily cron / manual |
| `send_welcome_email` | `welcome_student` | On student creation |
| `send_enrollment_confirmation_email` | `enrollment_child` | On enrollment |
| `send_fun_friday_email` | `fun_friday` | Weekly manual |
| `send_payment_reminder_email` | `payment_reminder` | Monthly manual |
| `send_quarterly_receipt_email` | `receipt_quarterly_child` | Quarterly manual |
| `send_vacation_closure_email` | `vacation_closure` | Manual |
| `send_tax_certificate_email` | `tax_certificate` | Yearly (April) |
| `send_all_tax_certificates` | (iterates parents) | Yearly batch |
| `send_monthly_report` | `monthly_report` | Monthly manual |
| `generate_tax_certificate_pdf` | (HTML to PDF) | Called by tax certificate |

## Celery Tasks (`comms/tasks.py`)

All tasks have retry logic (3 retries, exponential backoff):

| Task | Purpose | Trigger |
| ---- | ------- | ------- |
| `send_welcome_email_task` | Async welcome email | On student creation |
| `send_birthday_email_task` | Individual birthday email | Called by batch task |
| `send_birthday_emails_task` | Daily birthday batch | Celery Beat (8:00 AM) |
| `send_payment_reminders` | Weekly payment reminder batch | Celery Beat |
| `send_generic_email_task` | Generic email dispatcher | Manual |
| `send_enrollment_confirmation_task` | Enrollment confirmation with attachments (uses `student.gender` field) | On enrollment |

Without Redis, Celery runs in eager mode (synchronous, same process).

## Management Commands

### `send_email`

```bash
python manage.py send_email --template happy_birthday --test
python manage.py send_email --fun-friday --activity "Zumba" --date 2025-10-10 --time 17:00-18:30
python manage.py send_email --payment-reminder --month octubre
python manage.py send_email --tax-certificate --year 2024
```

### `test_all_emails`

```bash
python manage.py test_all_emails                     # Send all 11 test emails
python manage.py test_all_emails --only fun_friday,birthday
python manage.py test_all_emails --list              # List available templates
python manage.py test_all_emails --to admin@test.com
```

## URL Patterns (comms/urls.py)

10 URL patterns for the email app form views (`apps/`, `apps/fun-friday/`, `apps/payment-reminder/`, etc.). Views are imported from `core.views.app_forms`.

## Tests

Tests for comms services live in `project/tests/`:

| File | What it tests |
| ---- | ------------- |
| `test_email_service.py` | `EmailService` — basic send, multiple recipients, CC/BCC, attachments, fail_silently, bulk sends, bad template handling. Uses `django.core.mail.outbox` (locmem backend). |
| `test_email_functions.py` | All convenience functions in `email_functions.py` — correct template, subject, context, and fail_silently for each function |

Run with `make test` (requires Docker + PostgreSQL running).

## Cross-App Communication

- **Depends on**: students (Student, Parent for recipient resolution), billing (Payment for tax certificates)
- **Depended on by**: core views (student creation triggers welcome email task, app form views send emails)
- **Imported by**: `core/views/students.py` imports `comms.tasks.send_welcome_email_task`; `core/views/app_forms.py` imports email functions and email_service
