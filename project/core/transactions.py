from datetime import date
from django.db.models import Q, Prefetch
from core.models import Payment, Student, Parent, Enrollment, EnrollmentType, Group, Teacher

# Read logic

all_students = Student.objects.filter(active=True).select_related("group", "group__teacher").prefetch_related("parents",
                                            Prefetch("enrollments",queryset=Enrollment.objects.select_related("enrollment_type")))

def payments_for_last_two_school_years():
    today = date.today()
    if today.month >= 9:
        current_school_start_year = today.year
    else:
        current_school_start_year = today.year - 1
    start_year = current_school_start_year - 1
    end_year = current_school_start_year + 1
    start_date = date(start_year, 9, 1)
    end_date = date(end_year, 8, 31)

    date_filter = (
        Q(payment_date__range=(start_date, end_date)) |
        Q(due_date__range=(start_date, end_date)) |
        Q(created_at__date__range=(start_date, end_date))
    )

    payments_qs = (
        Payment.objects
        .filter(date_filter)
        .select_related(
            "student",
            "parent",
            "enrollment",
            "enrollment__enrollment_type",
        )
        .prefetch_related(
            "student__parents",
            "student__enrollments",
            Prefetch("student__group__teacher"),
        )
        .order_by("payment_date", "due_date", "created_at")
    )

    return payments_qs

all_payments = payments_for_last_two_school_years()


# Write logic


