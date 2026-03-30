# Enrollment & Payment System - Five a Day

## Academic Year

- Spans from the **first Monday on or after September 14th** to the **last Friday of June**.
- Annotated with two years, e.g. `2025-2026`.
- In student creation, only the years appear (e.g. "2025-2026"); actual dates are computed when saved to database.

---

## Enrollments

An enrollment represents a student being "inside the system" for an academic year. One enrollment per academic year per student.

### Enrollment Fees (once per academic year)

| Student Type       | Fee   | Notes                                            |
|--------------------|-------|--------------------------------------------------|
| New child          | 40€   | Default enrollment fee                           |
| Returning child    | 20€   | Old student discount: -20€ (already had an enrollment) |
| Adult (18+)        | 20€   | Fixed, no discounts                              |

### June Discount

- Students who **complete the academic year** (are still active in June) get a **-20€ discount** on their June payment.
- Applies regardless of when they were enrolled.
- Does **not** apply to adults.

---

## Payment Modalities

Each enrollment has a **payment modality** (monthly or quarterly), changeable at any time from the student detail view.

### Monthly Payments

| Schedule          | Description        | Price  |
|-------------------|--------------------|--------|
| 2 days/week       | Full-time (default)| 54€    |
| 1 day/week        | Part-time          | 36€    |

Monthly payments are due every month from **September** to **June**.

**Monthly Discounts:**
- **Sibling discount**: -5% for the younger sibling (both share the same parent)
- **Cheque idioma** (language ticket): -20€/month flat discount. Students with this must be reported to the government monthly.
- **June discount**: -20€ for completing the academic year

### Quarterly Payments

Quarters:
- **Q1**: October–December (includes September payment)
- **Q2**: January–March
- **Q3**: April–June

Quarterly amount = 3 months × monthly fee × 0.95 (5% discount).

- **No further discounts** for quarterly modality (no sibling, no language cheque).
- Quarterly students are notified at the **start of each quarter**.
- Monthly students are notified **each month**.

### Special Payments

- Always treated as **monthly, 2 days/week**.
- Have their own custom logic and price (set manually).

---

## Adult Students (18+)

- **Enrollment**: 20€
- **Schedule**: Only 1 day/week monthly at **60€**
- **No discounts** of any kind
- **No parents**: adults have their own email and phone
- **Don't have**: allergies, GDPR, parents, school fields
- Student creation for adults skips the parent creation step

---

## Automatic Payment Generation

At the **start of each payment period**, a pending (due, not paid) payment is automatically created for every enrolled student:

- **Monthly students**: A payment is created at the start of each month (September through June).
- **Quarterly students**: A payment is created at the start of each quarter:
  - October 1 (Q1, covers September–December)
  - January 1 (Q2, covers January–March)
  - April 1 (Q3, covers April–June)

### Payment Amount Calculation

**Monthly (children, 2 days/week):**
```
base = full_time_monthly_fee (54€)
- sibling_discount if applicable (-5%)
- language_cheque_discount if applicable (-20€)
- june_discount if June and completing year (-20€)
```

**Monthly (children, 1 day/week):**
```
base = part_time_monthly_fee (36€)
- sibling_discount if applicable (-5%)
- language_cheque_discount if applicable (-20€)
- june_discount if June and completing year (-20€)
```

**Quarterly (children):**
```
base = 3 × monthly_fee × 0.95
No further discounts.
```

**Adult monthly:**
```
base = adult_group_monthly_fee (60€)
No discounts.
```

---

## Student Types in UI

### /students View Filters
- **All**: Show all students
- **Children**: Show students where `is_adult = False`
- **Adults**: Show students where `is_adult = True`

### Student Creation Buttons
1. **Nuevo Estudiante** (default): Creates parent first, then student (existing flow)
2. **Estudiante Adulto**: Creates adult student directly (no parent needed)
3. **Estudiante con padre existente**: Search for existing parent, then create student

---

## /payments View

### Filter by Payment Type
- Monthly 2 days/week
- Monthly 1 day/week
- Quarterly

### Filter by Status
- Not completed (pending, overdue, failed)
- All

### Quick Payment Completion
- Each unpaid payment row shows a payment icon (instead of the student icon)
- Clicking the icon reveals a dropdown with payment methods (Cash, Transfer, Credit Card)
- Selecting a method immediately completes the payment with that method

---

## Configuration (via /management)

All prices and discounts are managed through the `/management` view and stored in `SiteConfiguration`:

- `children_enrollment_fee`: 40€
- `adult_enrollment_fee`: 20€
- `full_time_monthly_fee`: 54€ (2 days/week)
- `part_time_monthly_fee`: 36€ (1 day/week)
- `adult_group_monthly_fee`: 60€
- `old_student_discount`: 20€ (flat)
- `june_discount`: 20€ (flat)
- `language_cheque_discount`: 20€ (flat, monthly)
- `quarterly_discount`: 5% (percentage)
- `sibling_discount`: 5% (percentage, monthly)
