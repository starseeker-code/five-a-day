from datetime import date

from django.db.models import Prefetch, Q

from billing.models import Enrollment, Payment
from students.models import Student


def get_active_students():
    """Return a queryset of active students with related data pre-fetched."""
    return (
        Student.objects.filter(active=True)
        .select_related("group", "group__teacher")
        .prefetch_related(
            "parents",
            Prefetch(
                "enrollments",
                queryset=Enrollment.objects.select_related("enrollment_type"),
            ),
        )
    )


def get_payments_for_last_two_school_years():
    """Return payments from the last two school years with related data."""
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
        Q(payment_date__range=(start_date, end_date))
        | Q(due_date__range=(start_date, end_date))
        | Q(created_at__date__range=(start_date, end_date))
    )

    return (
        Payment.objects.filter(date_filter)
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
        .order_by("-created_at")
    )


def get_all_payments_unrestricted():
    """Return all payments without date restrictions, with related data."""
    return (
        Payment.objects.select_related(
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
        .order_by("-created_at")
    )
