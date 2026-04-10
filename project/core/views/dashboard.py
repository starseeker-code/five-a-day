import calendar as cal_module
from datetime import date
from decimal import Decimal

from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render

from core.constants import SCHEDULED_APPS
from core.models import TodoItem
from billing.models import Payment
from students.models import Student


def home(request):
    today = date.today()
    current_month = today.month
    current_year = today.year

    pending_payments = Payment.objects.filter(
        payment_status="pending",
        due_date__month=current_month,
        due_date__year=current_year,
    ).select_related("student")

    pending_count = pending_payments.count()

    pending_by_student = {}
    for payment in pending_payments:
        sid = payment.student_id
        if sid not in pending_by_student:
            pending_by_student[sid] = {
                "first_name": payment.student.first_name,
                "last_name": payment.student.last_name,
                "amounts": [],
            }
        pending_by_student[sid]["amounts"].append(payment.amount)

    pending_students_list = list(pending_by_student.values())
    pending_students_display = [v["first_name"] for v in pending_students_list[:5]]
    has_more_pending = len(pending_students_list) > 5
    all_pending_students = sorted(
        [
            {
                "display_name": "{} {}".format(
                    v["first_name"],
                    "".join(w[0].upper() + "." for w in v["last_name"].split() if w),
                ),
                "amount": sum(v["amounts"]),
            }
            for v in pending_students_list
        ],
        key=lambda x: x["display_name"],
    )

    birthday_students = Student.objects.filter(
        active=True, birth_date__month=current_month
    ).order_by("birth_date__day")

    birthday_count = birthday_students.count()

    birthdays_display = [
        {"name": s.first_name, "day": s.birth_date.day} for s in birthday_students[:5]
    ]
    has_more_birthdays = birthday_count > 5

    days_in_month = cal_module.monthrange(current_year, current_month)[1]
    upcoming_events = []
    for app in SCHEDULED_APPS:
        if not app.get("active"):
            continue
        if app["frequency"] == "every_friday":
            for day in range(today.day, days_in_month + 1):
                d = date(current_year, current_month, day)
                if d.weekday() == 4:
                    upcoming_events.append({"name": app["name"], "date": d, "url_name": app["url_name"], "is_fun_friday": app["name"] == "Fun Friday"})
        elif app["frequency"] == "monthly_day_1":
            d = date(current_year, current_month, 1)
            if d >= today:
                upcoming_events.append({"name": app["name"], "date": d, "url_name": app["url_name"]})

    upcoming_events.sort(key=lambda x: x["date"])
    upcoming_events_count = len(upcoming_events)
    next_event = upcoming_events[0] if upcoming_events else None

    expected_payments = Payment.objects.filter(
        due_date__month=current_month,
        due_date__year=current_year,
    )
    expected_revenue = expected_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    completed_payments = Payment.objects.filter(
        payment_status="completed",
        payment_date__month=current_month,
        payment_date__year=current_year,
    )
    monthly_income_count = completed_payments.count()
    monthly_income_total = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    todos = TodoItem.objects.filter().order_by("due_date", "created_at")
    overdue_todos_count = TodoItem.objects.filter(due_date__lt=today).count()

    today_birthday_students = Student.objects.filter(
        active=True,
        birth_date__month=today.month,
        birth_date__day=today.day,
    ).order_by("first_name")[:5]
    today_birthday_names = [s.first_name for s in today_birthday_students]

    context = {
        "pending_payments_count": pending_count,
        "pending_students": pending_students_display,
        "has_more_pending": has_more_pending,
        "total_pending_students": len(pending_students_list),
        "all_pending_students": all_pending_students,
        "birthday_count": birthday_count,
        "birthdays": birthdays_display,
        "has_more_birthdays": has_more_birthdays,
        "current_month_name": today.strftime("%B"),
        "upcoming_events_count": upcoming_events_count,
        "upcoming_events": upcoming_events[:5],
        "next_event": next_event,
        "expected_revenue": expected_revenue,
        "monthly_income_count": monthly_income_count,
        "monthly_income_total": monthly_income_total,
        "todos": todos,
        "overdue_todos_count": overdue_todos_count,
        "today_birthday_names": today_birthday_names,
        "today": today,
    }

    return render(request, "home.html", context)


def all_info(request):
    from core.transactions import get_active_students, get_all_payments_unrestricted

    DB_PAGE_SIZE = 20

    # ── Students sorting ──
    students_sort = request.GET.get("students_sort", "date_desc")
    students_order = {
        "id_asc": "id",
        "first_name_asc": "first_name",
        "last_name_asc": "last_name",
        "date_desc": "-created_at",
    }.get(students_sort, "-created_at")
    students_qs = get_active_students().order_by(students_order)
    students_paginator = Paginator(students_qs, DB_PAGE_SIZE)
    students_page = students_paginator.get_page(request.GET.get("students_page", 1))

    # ── Payments sorting ──
    payments_sort = request.GET.get("payments_sort", "date_desc")
    payments_order = {
        "date_desc": "-created_at",
        "student_asc": ("student__first_name", "student__last_name"),
    }.get(payments_sort, "-created_at")
    if isinstance(payments_order, tuple):
        payments_qs = get_all_payments_unrestricted().order_by(*payments_order)
    else:
        payments_qs = get_all_payments_unrestricted().order_by(payments_order)
    payments_paginator = Paginator(payments_qs, DB_PAGE_SIZE)
    payments_page = payments_paginator.get_page(request.GET.get("payments_page", 1))

    return render(
        request,
        "all_info.html",
        {
            "students": students_page,
            "students_sort": students_sort,
            "students_total": students_paginator.count,
            "payments": payments_page,
            "payments_sort": payments_sort,
            "payments_total": payments_paginator.count,
        },
    )
