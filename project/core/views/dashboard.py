import calendar as cal_module
import json
import logging
from datetime import date
from decimal import Decimal

import httpx
from django.core.paginator import Paginator
from django.db.models import Case, DecimalField, Sum, Value, When
from django.shortcuts import render

from billing.models import Payment
from core.constants import SCHEDULED_APPS
from core.models import TodoItem
from students.models import Student

logger = logging.getLogger(__name__)

_QUOTE_COOKIE = "inspirational_quotes"
_QUOTE_COOKIE_TTL = 48 * 60 * 60  # 48 hours in seconds
_QUOTE_API_URL = (
    "https://zenquotes.io/api/quotes"  # no trailing slash — the API 301-redirects "/api/quotes/" → "/api/quotes"
)


def _get_quote(request):
    """
    Returns (quote_text, author_or_None, new_cookie_value_or_None).

    Reads two quotes stored in a cookie (48h TTL). Day 0 shows the first quote,
    day 1+ shows the second. When the cookie is missing or expired, fetches fresh
    quotes from zenquotes.io. On API failure, falls back to the default subtitle.
    new_cookie_value is non-None only when the cookie needs to be written.
    """
    raw = request.COOKIES.get(_QUOTE_COOKIE)
    today = date.today()

    if raw:
        try:
            data = json.loads(raw)
            quotes = data["quotes"]
            stored = date.fromisoformat(data["date"])
            idx = min((today - stored).days, len(quotes) - 1)
            q = quotes[idx]
            return q["q"], q["a"], None
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            pass

    # Cookie missing, corrupt, or expired — fetch from API
    try:
        # follow_redirects=True guards against future URL changes (the API has already moved once)
        resp = httpx.get(_QUOTE_API_URL, timeout=5.0, follow_redirects=True)
        resp.raise_for_status()
        items = resp.json()
        quotes = [{"q": item["q"], "a": item["a"]} for item in items[:2] if item.get("q") and item["q"] != "[AUTH]"]
        if quotes:
            cookie_val = json.dumps({"date": today.isoformat(), "quotes": quotes})
            return quotes[0]["q"], quotes[0]["a"], cookie_val
        logger.warning(
            "zenquotes API returned no usable quotes (got %d items)", len(items) if isinstance(items, list) else 0
        )
    except Exception as e:
        # Log but don't break the page — fall back to the default subtitle below.
        logger.warning("zenquotes API fetch failed: %s: %s", type(e).__name__, e)

    return "¡Cada día es una nueva oportunidad para inspirar!", None, None


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

    birthday_students = list(
        Student.objects.filter(active=True, birth_date__month=current_month).order_by("birth_date__day")
    )

    birthday_count = len(birthday_students)

    birthdays_display = [
        {
            "name": s.first_name,
            "day": s.birth_date.day,
            "age": today.year
            - s.birth_date.year
            - (1 if (today.month, today.day) < (s.birth_date.month, s.birth_date.day) else 0),
        }
        for s in birthday_students[:5]
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
                    upcoming_events.append(
                        {
                            "name": app["name"],
                            "date": d,
                            "url_name": app["url_name"],
                            "is_fun_friday": app["name"] == "Fun Friday",
                        }
                    )
        elif app["frequency"] == "monthly_day_1":
            d = date(current_year, current_month, 1)
            if d >= today:
                upcoming_events.append({"name": app["name"], "date": d, "url_name": app["url_name"]})

    upcoming_events.sort(key=lambda x: x["date"])
    upcoming_events_count = len(upcoming_events)
    next_event = upcoming_events[0] if upcoming_events else None

    _zero = Decimal("0.00")
    revenue_stats = Payment.objects.aggregate(
        expected_revenue=Sum(
            Case(
                When(due_date__month=current_month, due_date__year=current_year, then="amount"),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        monthly_income_total=Sum(
            Case(
                When(
                    payment_status="completed",
                    payment_date__month=current_month,
                    payment_date__year=current_year,
                    then="amount",
                ),
                default=Value(0),
                output_field=DecimalField(),
            )
        ),
        monthly_income_count=Sum(
            Case(
                When(
                    payment_status="completed",
                    payment_date__month=current_month,
                    payment_date__year=current_year,
                    then=Value(1),
                ),
                default=Value(0),
            )
        ),
    )
    expected_revenue = revenue_stats["expected_revenue"] or _zero
    monthly_income_total = revenue_stats["monthly_income_total"] or _zero
    monthly_income_count = revenue_stats["monthly_income_count"] or 0

    todos = list(TodoItem.objects.order_by("due_date", "created_at"))
    overdue_todos_count = sum(1 for t in todos if t.is_overdue)

    today_birthday_students = Student.objects.filter(
        active=True,
        birth_date__month=today.month,
        birth_date__day=today.day,
    ).order_by("first_name")[:5]
    today_birthday_names = [s.first_name for s in today_birthday_students]

    quote_text, quote_author, new_cookie = _get_quote(request)

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
        "inspirational_quote": quote_text,
        "inspirational_author": quote_author,
    }

    response = render(request, "home.html", context)
    if new_cookie is not None:
        response.set_cookie(
            _QUOTE_COOKIE,
            new_cookie,
            max_age=_QUOTE_COOKIE_TTL,
            httponly=True,
            samesite="Lax",
        )
    return response


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
