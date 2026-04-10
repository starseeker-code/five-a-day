# billing — Payments, Enrollments, Pricing

The `billing` app owns all financial logic: pricing configuration, enrollment plans, payment tracking, and data exports. It contains the service layer where core business logic lives.

## Models

| Model | Table | Key Fields |
| ----- | ----- | ---------- |
| **SiteConfiguration** | `site_configuration` | Singleton (pk=1). All pricing: enrollment fees, monthly fees, discount percentages/amounts |
| **EnrollmentType** | `enrollment_types` | name (monthly, quarterly, adults, special), display_name, base amounts |
| **Enrollment** | `enrollments` | FK to Student + EnrollmentType. schedule_type, payment_modality, discounts, amounts, status, academic_year |
| **Payment** | `payments` | FK to Student + Parent + Enrollment. amount, type, method, status, due_date, payment_date |

### Key Business Rules

- **SiteConfiguration** is a singleton — `get_config()` uses `get_or_create()` (race-condition safe), seeded from `billing/constants.py`
- **One active enrollment per student** — enforced by UniqueConstraint on `(student)` where `status='active'`
- **Payment.is_overdue** — True when status is pending and due_date < today
- **Enrollment.is_paid** / **remaining_amount** — calculated from completed payment totals

### Helper Functions (in models.py)

- `current_academic_year(date)` — returns "YYYY-YYYY" format (year starts in September)
- `academic_year_start_date(year)` — first Monday on/after September 14th
- `academic_year_end_date(year)` — last Friday in June

## Service Layer

### EnrollmentService (`billing/services/enrollment_service.py`)

- `create_enrollment(student, enrollment_data, is_adult)` — creates an Enrollment within `transaction.atomic()` with proper pricing and discounts. Raises `ValueError` if required EnrollmentType is missing.
- `_resolve_plan(config, data, ...)` — determines enrollment type, base amount, schedule type, payment modality
- `_apply_discounts(config, base, ...)` — applies sibling and language cheque discounts

### PaymentService (`billing/services/payment_service.py`)

- `calculate_monthly_amount(enrollment, config, month)` — monthly payment with discounts + June bonus
- `calculate_quarterly_amount(enrollment, config, quarter_due_month)` — 3 months minus quarterly discount
- `complete_payment(payment_id)` — marks payment completed with today's date (within `transaction.atomic()`)
- `should_generate_monthly/quarterly(month)` — academic calendar validation
- `get_payment_statistics(month, year)` — aggregate pending/completed counts and totals

### PricingService (`billing/services/pricing_service.py`)

- `get_config()` — cached SiteConfiguration access
- `get_monthly_fee(schedule_type)` — fee by full_time/part_time/adult_group
- `get_enrollment_fee(is_adult)` — child vs adult enrollment fee
- `calculate_quarterly_price()` — 3 months * full_time - discount%

## Constants (billing/constants.py)

- Pricing seed values (used in SiteConfiguration defaults)
- Choice tuples: ENROLLMENT_TYPE_CHOICES, SCHEDULE_TYPE_CHOICES, PAYMENT_MODALITY_CHOICES, etc.
- QUARTERS definition (Q1: Oct-Dec, Q2: Jan-Mar, Q3: Apr-Jun)
- Utility functions: `calculate_discount()`, `get_monthly_fee_by_schedule()`, `get_enrollment_fee()`

## Management Commands

### `generate_payments`

```bash
python manage.py generate_payments              # Current month
python manage.py generate_payments --month 10 --year 2025
python manage.py generate_payments --dry-run    # Preview only
```

Generates pending payments for all active enrollments. Monthly students get one per month (Sep-Jun). Quarterly students get one per quarter (Oct, Jan, Apr). Skips if payment already exists for that period.

## URL Patterns (billing/urls.py)

Payment CRUD, enrollment API, management panel, search/statistics, CSV/Excel export. 20 URL patterns total.

## Cross-App Communication

- **Depends on**: students (FK to Student, Parent in Enrollment and Payment models)
- **Depended on by**: core views (dashboard shows payment stats), comms (email functions reference Payment for tax certificates)
- **Exports used by core**: `SiteConfiguration`, `Enrollment`, `Payment`, `current_academic_year`, service classes
