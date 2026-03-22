from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages

# from django.views import View
from django.views.generic import FormView, DetailView, ListView, UpdateView, CreateView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from .models import *
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse_lazy, reverse
from decimal import Decimal, InvalidOperation
import json
from datetime import date, datetime
from core.transactions import all_students, all_payments
from core.forms import StudentForm, ParentForm, EnrollmentForm, ParentFormSet
from core.email import email_service
from core import constants
from django.template.loader import render_to_string
from django.conf import settings
import os

# Registry of scheduled apps/emails.
# frequency options: 'every_friday' | 'monthly_day_1' | 'manual' | 'yearly_april'
#                    'monthly_last_day' | 'on_student_creation' | 'daily'
#                    'quarterly' | 'on_enrollment'
SCHEDULED_APPS = [
    {"name": "Fun Friday", "url_name": "fun_friday_view", "frequency": "every_friday", "active": True},
    {"name": "Pago Mensual", "url_name": "payment_reminder_form", "frequency": "monthly_day_1", "active": True},
    {"name": "Vacaciones", "url_name": "vacation_closure_form", "frequency": "manual", "active": True},
    {"name": "Certificado Renta", "url_name": "tax_certificate_form", "frequency": "yearly_april", "active": True},
    {"name": "Informe Mensual", "url_name": "monthly_report_form", "frequency": "monthly_last_day", "active": True},
    {"name": "Bienvenida", "url_name": "welcome_form", "frequency": "on_student_creation", "active": True},
    {"name": "Cumpleaños", "url_name": "birthday_form", "frequency": "daily", "active": True},
    {"name": "Recibos", "url_name": "receipts_form", "frequency": "quarterly", "active": True},
    {"name": "Matrículas", "url_name": "enrollment_form", "frequency": "on_enrollment", "active": True},
]

# Nombres de días y meses en español (shared across app views)
DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
            "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def parse_date_value(date_value):
    """Parse date strings supporting dd/mm/yyyy and yyyy-mm-dd formats."""
    if not date_value:
        return None
    if isinstance(date_value, date):
        return date_value

    raw_value = str(date_value).strip()
    if not raw_value:
        return None

    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw_value, fmt).date()
        except ValueError:
            continue

    raise ValidationError(
        f"Formato de fecha inválido: '{raw_value}'. Usa dd/mm/yyyy."
    )


# ============================================================================
# ERROR HANDLERS
# ============================================================================

def handler400(request, exception=None):
    return render(request, "400.html", status=400)

def handler403(request, exception=None):
    return render(request, "403.html", status=403)

def handler404(request, exception=None):
    return render(request, "404.html", status=404)

def handler405(request, exception=None):
    return render(request, "405.html", status=405)

def handler500(request):
    return render(request, "500.html", status=500)


# ── Test endpoints (render error pages directly for inspection) ──────────────

def test_error_400(request):
    return render(request, "400.html", status=400)

def test_error_403(request):
    return render(request, "403.html", status=403)

def test_error_404(request):
    return render(request, "404.html", status=404)

def test_error_405(request):
    return render(request, "405.html", status=405)

def test_error_500(request):
    return render(request, "500.html", status=500)


@csrf_exempt
def health_check(request):
    """
    Endpoint de salud para Render.com y otros servicios de monitoreo.
    Retorna 200 OK si la aplicación está funcionando.
    """
    return JsonResponse(
        {
            "status": "healthy",
            "service": "fiveaday",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        status=200,
    )


def login_view(request):
    """Vista de login con credenciales desde .env"""
    if request.session.get("is_authenticated"):
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        valid_username = os.getenv("LOGIN_USERNAME", "fiveaday")
        valid_password = os.getenv("LOGIN_PASSWORD", "Fiveaday123!")

        if username == valid_username and password == valid_password:
            request.session["is_authenticated"] = True
            request.session["username"] = username
            return redirect("home")
        else:
            messages.error(request, "❌ Usuario o contraseña incorrectos")

    google_oauth_available = bool(
        os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET")
    )
    return render(request, "login.html", {"google_oauth_available": google_oauth_available})


_GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
]

import logging as _logging
_oauth_log = _logging.getLogger(__name__)


def _google_callback_uri(request):
    """Return the OAuth callback URI — prefer explicit env var over build_absolute_uri."""
    explicit = os.getenv("GOOGLE_REDIRECT_URI")
    if explicit:
        return explicit
    return request.build_absolute_uri(reverse("google_oauth_callback"))


def _build_flow(client_id, client_secret, callback_uri, state=None):
    from google_auth_oauthlib.flow import Flow
    cfg = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [callback_uri],
        }
    }
    kwargs = {"scopes": _GOOGLE_SCOPES}
    if state:
        kwargs["state"] = state
    flow = Flow.from_client_config(cfg, **kwargs)
    flow.redirect_uri = callback_uri
    return flow


def google_oauth_redirect(request):
    """Redirect the browser to Google's OAuth2 consent screen."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        messages.error(request, "Google OAuth no está configurado.")
        return redirect("login")

    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    callback_uri = _google_callback_uri(request)
    _oauth_log.info("OAuth redirect → callback_uri=%s", callback_uri)
    flow = _build_flow(client_id, client_secret, callback_uri)
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )
    request.session["google_oauth_state"] = state
    return redirect(authorization_url)


def google_oauth_callback(request):
    """Handle the OAuth2 redirect from Google and establish a session."""
    import urllib.parse
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    # Checked backend-only — never sent to the frontend
    allowed_email = (
        os.getenv("GOOGLE_ALLOWED_EMAIL")
        or os.getenv("EMAIL_HOST_USER")
        or os.getenv("DJANGO_SUPERUSER_EMAIL", "")
    )

    if settings.DEBUG:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    state = request.session.get("google_oauth_state")
    if not state or state != request.GET.get("state"):
        _oauth_log.warning("OAuth state mismatch: session=%s, param=%s", state, request.GET.get("state"))
        messages.error(request, "Estado OAuth inválido. Inténtalo de nuevo.")
        return redirect("login")

    callback_uri = _google_callback_uri(request)
    _oauth_log.info("OAuth callback → callback_uri=%s", callback_uri)
    flow = _build_flow(client_id, client_secret, callback_uri, state=state)

    # Reconstruct authorization_response using the configured base URI so it
    # matches exactly the redirect_uri registered in Google Console.
    parsed = urllib.parse.urlparse(callback_uri)
    query = request.META.get("QUERY_STRING", "")
    authorization_response = urllib.parse.urlunparse(parsed._replace(query=query))
    _oauth_log.info("OAuth callback → authorization_response=%s", authorization_response)

    try:
        flow.fetch_token(authorization_response=authorization_response)
    except Exception:
        _oauth_log.exception("OAuth fetch_token failed")
        messages.error(request, "Error al obtener el token de Google. Inténtalo de nuevo.")
        return redirect("login")

    credentials = flow.credentials

    try:
        id_info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            client_id,
        )
        user_email = id_info.get("email", "")
        user_name = id_info.get("given_name", user_email.split("@")[0])
    except Exception:
        _oauth_log.exception("OAuth id_token verification failed")
        messages.error(request, "Error al verificar la identidad de Google.")
        return redirect("login")

    # Backend-only check — email never exposed to frontend
    if user_email.lower() != allowed_email.lower():
        _oauth_log.warning("OAuth email mismatch: got=%s expected=%s", user_email, allowed_email)
        messages.error(request, "❌ Esta cuenta de Google no tiene acceso.")
        return redirect("login")

    request.session["is_authenticated"] = True
    request.session["username"] = user_name
    request.session["google_authenticated"] = True
    # Store credentials so other views can reuse them for Gmail / Sheets
    request.session["google_credentials"] = {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": list(credentials.scopes) if credentials.scopes else [],
    }
    return redirect("home")


def logout_view(request):
    """Vista de logout"""
    request.session.flush()  # Eliminar toda la sesión
    messages.success(request, "✅ Has cerrado sesión correctamente")
    return redirect("login")


def home(request):
    import calendar as cal_module
    from datetime import date
    from django.db.models import Sum
    from .models import Payment, Student, TodoItem

    today = date.today()
    current_month = today.month
    current_year = today.year

    # Pagos pendientes de este mes (due_date en este mes y status pending)
    pending_payments = Payment.objects.filter(
        payment_status="pending",
        due_date__month=current_month,
        due_date__year=current_year,
    ).select_related("student")

    pending_count = pending_payments.count()

    # Obtener nombres únicos de estudiantes con pagos pendientes y sus totales
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

    # Cumpleaños este mes (estudiantes activos)
    birthday_students = Student.objects.filter(
        active=True, birth_date__month=current_month
    ).order_by("birth_date__day")

    birthday_count = birthday_students.count()

    # Lista de cumpleaños con nombre y día (máximo 5)
    birthdays_display = [
        {"name": s.first_name, "day": s.birth_date.day} for s in birthday_students[:5]
    ]
    has_more_birthdays = birthday_count > 5

    # ESPACIO 1 - Próximas apps/emails programadas este mes
    days_in_month = cal_module.monthrange(current_year, current_month)[1]
    upcoming_events = []
    for app in SCHEDULED_APPS:
        if not app.get("active"):
            continue
        if app["frequency"] == "every_friday":
            for day in range(today.day, days_in_month + 1):
                d = date(current_year, current_month, day)
                if d.weekday() == 4:  # Friday
                    upcoming_events.append({"name": app["name"], "date": d, "url_name": app["url_name"], "is_fun_friday": app["name"] == "Fun Friday"})
        elif app["frequency"] == "monthly_day_1":
            d = date(current_year, current_month, 1)
            if d >= today:
                upcoming_events.append({"name": app["name"], "date": d, "url_name": app["url_name"]})

    upcoming_events.sort(key=lambda x: x["date"])
    upcoming_events_count = len(upcoming_events)
    next_event = upcoming_events[0] if upcoming_events else None

    # ESPACIO 2 - Ingresos del mes
    # Expected revenue: all payments due this month (any status)
    expected_payments = Payment.objects.filter(
        due_date__month=current_month,
        due_date__year=current_year,
    )
    expected_revenue = expected_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Actual revenue: completed payments this month
    completed_payments = Payment.objects.filter(
        payment_status="completed",
        payment_date__month=current_month,
        payment_date__year=current_year,
    )
    monthly_income_count = completed_payments.count()
    monthly_income_total = completed_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # ToDo items
    todos = TodoItem.objects.filter().order_by("due_date", "created_at")
    overdue_todos_count = TodoItem.objects.filter(due_date__lt=today).count()

    # Today's birthdays (names)
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
        # ESPACIO 1
        "upcoming_events_count": upcoming_events_count,
        "upcoming_events": upcoming_events[:5],
        "next_event": next_event,
        # ESPACIO 2
        "expected_revenue": expected_revenue,
        "monthly_income_count": monthly_income_count,
        "monthly_income_total": monthly_income_total,
        # ToDo list
        "todos": todos,
        "overdue_todos_count": overdue_todos_count,
        "today_birthday_names": today_birthday_names,
        "today": today,
    }

    return render(request, "home.html", context)


@require_http_methods(["POST"])
def create_todo(request):
    from .models import TodoItem

    try:
        data = json.loads(request.body)
        text = data.get("text", "").strip()
        due_date_str = data.get("due_date", "")

        if not text:
            return JsonResponse({"success": False, "error": "El texto no puede estar vacío"}, status=400)
        if not due_date_str:
            return JsonResponse({"success": False, "error": "La fecha es obligatoria"}, status=400)

        due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
        todo = TodoItem.objects.create(text=text, due_date=due_date)

        return JsonResponse({
            "success": True,
            "todo": {
                "id": todo.id,
                "text": todo.text,
                "due_date_iso": todo.due_date.isoformat(),
                "due_date_display": todo.due_date.strftime("%d/%m/%Y"),
                "is_overdue": todo.is_overdue,
            },
        })
    except (ValueError, json.JSONDecodeError) as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)


@require_http_methods(["POST"])
def complete_todo(request, todo_id):
    from .models import TodoItem

    todo = get_object_or_404(TodoItem, id=todo_id)
    todo.delete()
    return JsonResponse({"success": True})


def all_info(request):
    from core.transactions import all_students, all_payments_unrestricted

    DB_PAGE_SIZE = 20

    # ── Students sorting ──
    students_sort = request.GET.get("students_sort", "date_desc")
    students_order = {
        "id_asc": "id",
        "first_name_asc": "first_name",
        "last_name_asc": "last_name",
        "date_desc": "-created_at",
    }.get(students_sort, "-created_at")
    students_qs = all_students.order_by(students_order)
    students_paginator = Paginator(students_qs, DB_PAGE_SIZE)
    students_page = students_paginator.get_page(request.GET.get("students_page", 1))

    # ── Payments sorting ──
    payments_sort = request.GET.get("payments_sort", "date_desc")
    payments_order = {
        "date_desc": "-created_at",
        "student_asc": ("student__first_name", "student__last_name"),
    }.get(payments_sort, "-created_at")
    if isinstance(payments_order, tuple):
        payments_qs = all_payments_unrestricted.order_by(*payments_order)
    else:
        payments_qs = all_payments_unrestricted.order_by(payments_order)
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


def apps_view(request):
    """Vista para la página de aplicaciones/herramientas"""
    return render(request, "apps.html")



# ---> Estudiantes | Pagos || DASHBOARDS (Home + Info) | Aplicaciones | Facturacion | UI! || Gastos | Renta | UI!! || Configuracion | Contacto y ayuda


class StudentsView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = "student_create.html"

    success_url = reverse_lazy(
        "student_create"
    )  # TODO: Volver al mismo lugar para crear

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if "parent_form" not in context:
            context["parent_form"] = ParentForm(self.request.POST or None)
        if "enrollment_form" not in context:
            context["enrollment_form"] = EnrollmentForm(self.request.POST or None)
        return context

    def form_valid(self, form):
        parent_form = ParentForm(self.request.POST)
        enrollment_form = EnrollmentForm(self.request.POST)
        if not (parent_form.is_valid() and enrollment_form.is_valid()):
            return self.form_invalid(form)
        try:
            with transaction.atomic():
                parent_dni = parent_form.cleaned_data.get("dni")
                if parent_dni:
                    parent_dni = parent_dni.strip().upper()
                parent, created = Parent.objects.get_or_create(
                    dni=parent_dni,
                    defaults={
                        "first_name": parent_form.cleaned_data.get("first_name"),
                        "last_name": parent_form.cleaned_data.get("last_name"),
                        "phone": parent_form.cleaned_data.get("phone"),
                        "email": parent_form.cleaned_data.get("email"),
                        "iban": parent_form.cleaned_data.get("iban", "") or "",
                    },
                )
                if not created:
                    for field in ("first_name", "last_name", "phone", "email", "iban"):
                        val = parent_form.cleaned_data.get(field)
                        if val is not None:
                            setattr(parent, field, val)
                    parent.save()
                self.object = form.save()
                self.object.parents.add(parent)
                enrollment = enrollment_form.create_enrollment(self.object)
                messages.success(
                    self.request,
                    f"¡Estudiante {self.object.full_name} creado exitosamente!",
                )

        except Exception as e:
            messages.error(self.request, f"Error al crear el estudiante: {str(e)}")
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)

        context["parent_form"] = ParentForm(self.request.POST or None)
        context["enrollment_form"] = EnrollmentForm(self.request.POST or None)
        return self.render_to_response(context)


# ============================================================================
# PARENT AND STUDENT MANAGEMENT - Parent-First Flow
# ============================================================================


class ParentCreateView(CreateView):
    """Vista para crear un nuevo padre/tutor"""

    model = Parent
    form_class = ParentForm
    template_name = "parent_create.html"

    def get_success_url(self):
        # Después de crear el padre, redirigir a crear estudiante con el parent_id
        return reverse_lazy("student_create") + f"?parent_id={self.object.id}"

    def form_valid(self, form):
        try:
            # Verificar si ya existe un padre con ese DNI
            dni = form.cleaned_data.get("dni")
            existing_parent = Parent.objects.filter(dni=dni).first()

            if existing_parent:
                messages.info(
                    self.request,
                    f"El padre/tutor {existing_parent.full_name} ya existe. "
                    f"Serás redirigido para crear un estudiante.",
                )
                self.object = existing_parent
                return HttpResponseRedirect(self.get_success_url())

            # Si no existe, crear el nuevo padre
            self.object = form.save()
            messages.success(
                self.request,
                f"Padre/tutor {self.object.full_name} creado exitosamente. "
                f"Ahora crea un estudiante para este padre.",
            )
            return HttpResponseRedirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, f"Error al crear el padre: {str(e)}")
            return self.form_invalid(form)


class StudentCreateView(CreateView):
    """
    Vista para crear un nuevo estudiante.
    Puede recibir un parent_id como parámetro GET para pre-vincular al padre.
    """

    model = Student
    form_class = StudentForm
    template_name = "student_create.html"

    def get_context_data(self, **kwargs):
        from .models import SiteConfiguration

        context = super().get_context_data(**kwargs)

        # Success state from redirect
        if self.request.GET.get("success"):
            context["show_success"] = True
            context["success_student_name"] = self.request.GET.get("student_name", "")
            context["success_fee"] = self.request.GET.get("fee", "")
            context["success_create_sibling"] = self.request.GET.get("create_sibling", "")
            context["success_parent_id"] = self.request.GET.get("parent_id", "")
            return context  # Skip loading form data for success page

        mode = self.request.GET.get("mode", "normal")
        context["creation_mode"] = mode
        context["is_adult_mode"] = mode == "adult"

        parent_id = self.request.GET.get("parent_id")
        if parent_id:
            try:
                parent = Parent.objects.get(id=parent_id)
                context["parent"] = parent
                context["parent_id"] = parent_id
            except Parent.DoesNotExist:
                messages.error(self.request, "El padre especificado no existe")

        if mode == "existing_parent":
            context["all_parents"] = Parent.objects.all().order_by("last_name", "first_name")

        if "enrollment_form" not in context:
            context["enrollment_form"] = EnrollmentForm(self.request.POST or None)

        context["groups"] = Group.objects.filter(active=True)

        config = SiteConfiguration.get_config()
        # Quarterly = 3 * full_time - 5%
        quarterly_price = config.full_time_monthly_fee * 3 * (1 - config.quarterly_enrollment_discount / 100)
        context["price_config"] = {
            "monthly_full": str(config.full_time_monthly_fee),
            "monthly_part": str(config.part_time_monthly_fee),
            "quarterly": str(quarterly_price),
            "adult_group": str(config.adult_group_monthly_fee),
        }
        context["enrollment_fee_children"] = str(config.children_enrollment_fee)
        context["enrollment_fee_adult"] = str(config.adult_enrollment_fee)
        context["language_cheque_discount"] = str(config.language_cheque_discount)
        context["sibling_discount"] = str(config.sibling_discount)

        # Students for sibling search (active, current year)
        context["all_students_for_sibling"] = Student.objects.filter(
            active=True
        ).select_related("group").order_by("first_name", "last_name")[:200]

        return context

    def form_valid(self, form):
        from core.tasks import send_welcome_email_task
        from .models import SiteConfiguration
        import calendar

        enrollment_form = EnrollmentForm(self.request.POST)

        if not enrollment_form.is_valid():
            return self.form_invalid(form)

        is_adult_mode = self.request.POST.get("is_adult_mode") == "true"

        try:
            with transaction.atomic():
                student = form.save(commit=False)
                if is_adult_mode:
                    student.is_adult = True
                    student.email = self.request.POST.get("adult_email", "")
                    student.phone = self.request.POST.get("adult_phone", "")
                student.save()

                parent = None
                parent_id = None

                if not is_adult_mode:
                    parent_id = self.request.POST.get("parent_id") or self.request.GET.get(
                        "parent_id"
                    )
                    if not parent_id:
                        messages.error(self.request, "Debe especificar un padre para el estudiante")
                        student.delete()
                        return self.form_invalid(form)
                    try:
                        parent = Parent.objects.get(id=parent_id)
                        student.parents.add(parent)
                    except Parent.DoesNotExist:
                        messages.error(self.request, "El padre especificado no existe")
                        student.delete()
                        return self.form_invalid(form)

                # Create enrollment
                enrollment = enrollment_form.create_enrollment(student, is_adult=is_adult_mode)

                # Create enrollment fee payment (pending, due end of month)
                config = SiteConfiguration.get_config()
                today = date.today()
                last_day = calendar.monthrange(today.year, today.month)[1]
                due_date = date(today.year, today.month, last_day)

                enrollment_fee = (
                    config.adult_enrollment_fee if is_adult_mode
                    else config.children_enrollment_fee
                )

                Payment.objects.create(
                    student=student,
                    parent=parent,
                    enrollment=enrollment,
                    payment_type='enrollment',
                    payment_method='transfer',
                    amount=enrollment_fee,
                    currency='EUR',
                    payment_status='pending',
                    due_date=due_date,
                    concept=f"Matrícula {enrollment.academic_year} — {student.full_name}",
                )

                # Enqueue welcome email
                try:
                    send_welcome_email_task.delay(
                        parent_id=parent.id if parent else None,
                        student_id=student.id,
                        enrollment_id=enrollment.id,
                    )
                except Exception:
                    pass

                # Redirect to success page with student info
                from urllib.parse import quote
                return HttpResponseRedirect(
                    reverse("student_create")
                    + f"?success=1&student_name={quote(student.full_name)}&student_id={student.id}"
                    + f"&fee={enrollment_fee}"
                    + (f"&parent_id={parent_id}&create_sibling=1" if "create_sibling" in self.request.POST and parent_id else "")
                )

        except Exception as e:
            messages.error(self.request, f"Error al crear el estudiante: {str(e)}")
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(
            self.request,
            "No se pudo crear el estudiante. Revisa los campos obligatorios.",
        )
        context = self.get_context_data(form=form)
        context["enrollment_form"] = EnrollmentForm(self.request.POST)
        return self.render_to_response(context)


class StudentListView(ListView):
    """Vista para listar todos los estudiantes"""

    model = Student
    template_name = "students.html"
    context_object_name = "students"

    def get_queryset(self):
        from .models import current_academic_year

        academic_year = current_academic_year()
        queryset = (
            Student.objects.filter(
                active=True,
                enrollments__academic_year=academic_year,
            )
            .distinct()
            .select_related("group")
            .prefetch_related("parents", "enrollments__enrollment_type")
        )

        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
            )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        from datetime import date, timedelta
        from .models import current_academic_year

        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["groups"] = Group.objects.filter(active=True)
        context["parents"] = Parent.objects.all()

        context["this_week_ids"] = get_ff_student_ids(get_next_friday())
        context["last_week_ids"] = get_ff_student_ids(get_last_friday())

        # Language cheque info for current academic year
        academic_year = current_academic_year()
        lc_student_ids = set(
            Enrollment.objects.filter(
                academic_year=academic_year,
                has_language_cheque=True,
                student__active=True,
            ).values_list("student_id", flat=True)
        )
        context["language_cheque_ids"] = lc_student_ids
        context["language_cheque_count"] = len(lc_student_ids)

        return context


class StudentUpdateView(UpdateView):
    """Vista para actualizar un estudiante existente"""

    model = Student
    form_class = StudentForm
    template_name = "student_update.html"
    pk_url_kwarg = "student_id"

    def get_success_url(self):
        return reverse_lazy("students_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener la matrícula activa
        try:
            enrollment = self.object.enrollments.filter(status="active").latest(
                "created_at"
            )
        except Enrollment.DoesNotExist:
            enrollment = None

        # Pre-fill enrollment form from current enrollment
        if "enrollment_form" not in context:
            initial = {}
            if enrollment:
                # Map back to plan choice
                if enrollment.payment_modality == 'quarterly':
                    initial['enrollment_plan'] = 'quarterly'
                elif enrollment.schedule_type == 'part_time':
                    initial['enrollment_plan'] = 'monthly_part'
                else:
                    initial['enrollment_plan'] = 'monthly_full'
                initial['discount'] = str(int(enrollment.discount_percentage))
                initial['has_language_cheque'] = enrollment.has_language_cheque
                initial['is_sibling_discount'] = enrollment.is_sibling_discount
            context["enrollment_form"] = EnrollmentForm(
                self.request.POST or None, initial=initial
            )

        context["parents"] = self.object.parents.all()
        context["groups"] = Group.objects.filter(active=True)

        return context

    def form_valid(self, form):
        enrollment_form = EnrollmentForm(self.request.POST)

        if not enrollment_form.is_valid():
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                student = form.save()

                # Deactivate old enrollment if exists
                student.enrollments.filter(status="active").update(status="finished")

                # Create new enrollment
                enrollment_form.create_enrollment(student, is_adult=student.is_adult)

                messages.success(
                    self.request,
                    f"Estudiante {student.full_name} actualizado exitosamente",
                )

        except Exception as e:
            messages.error(self.request, f"Error al actualizar el estudiante: {str(e)}")
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        context["enrollment_form"] = EnrollmentForm(self.request.POST)
        return self.render_to_response(context)


class StudentDetailView(DetailView):
    """Vista para ver detalles de un estudiante"""

    model = Student
    template_name = "student_detail.html"
    context_object_name = "student"
    pk_url_kwarg = "student_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["parents"] = self.object.parents.all()
        context["enrollments"] = self.object.enrollments.all().order_by("-created_at")
        context["payments"] = Payment.objects.filter(student=self.object).order_by(
            "-payment_date"
        )
        context["fun_friday_dates"] = self.object.fun_friday_dates.all()
        return context


# ============================================================================
# FUN FRIDAY DATE HELPERS  (reusable across views)
# ============================================================================

def get_next_friday(from_date=None):
    """Return this week's Friday (today if today is Friday, else next Friday)."""
    from datetime import date as _date, timedelta
    if from_date is None:
        from_date = _date.today()
    days_ahead = (4 - from_date.weekday()) % 7
    return from_date if days_ahead == 0 else from_date + timedelta(days=days_ahead)


def get_last_friday(from_date=None):
    """Return last week's Friday (7 days before get_next_friday)."""
    from datetime import timedelta
    return get_next_friday(from_date) - timedelta(days=7)


def get_ff_student_ids(friday_date):
    """Return a set of student IDs registered for the given Friday."""
    return set(
        FunFridayAttendance.objects.filter(date=friday_date).values_list('student_id', flat=True)
    )


# ============================================================================
# FUN FRIDAY ATTENDANCE API
# ============================================================================

@require_http_methods(["POST"])
def toggle_fun_friday_this_week(request, student_id):
    """Toggle a student's attendance for this week's Fun Friday."""
    student = get_object_or_404(Student, id=student_id)
    if student.is_adult:
        return JsonResponse({'success': False, 'error': 'Adult students cannot participate in Fun Friday'}, status=400)
    friday = get_next_friday()
    obj = FunFridayAttendance.objects.filter(student=student, date=friday).first()
    if obj:
        obj.delete()
        is_this_week = False
    else:
        FunFridayAttendance.objects.create(student=student, date=friday)
        is_this_week = True
    was_last_week = FunFridayAttendance.objects.filter(
        student=student, date=get_last_friday()
    ).exists()
    return JsonResponse({'success': True, 'is_this_week': is_this_week, 'was_last_week': was_last_week})


@require_http_methods(["POST"])
def add_fun_friday_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        from datetime import date as date_type
        from datetime import datetime
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        obj, created = FunFridayAttendance.objects.get_or_create(student=student, date=parsed_date)
        return JsonResponse({'success': True, 'created': created, 'date': str(parsed_date)})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


@require_http_methods(["POST"])
def remove_fun_friday_attendance(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    try:
        data = json.loads(request.body)
        date_str = data.get('date')
        from datetime import datetime
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        deleted, _ = FunFridayAttendance.objects.filter(student=student, date=parsed_date).delete()
        return JsonResponse({'success': True, 'deleted': deleted > 0})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# PAYMENT SEARCH AND HELPER APIs (keeping for compatibility)
# ============================================================================


def search_students(request):

    # Get all students with related data
    students = (
        Student.objects.select_related("group", "group__teacher")
        .prefetch_related("parents")
        .filter(active=True)
    )

    # Get all groups and parents for the form
    groups = Group.objects.filter(active=True).select_related("teacher")
    parents = Parent.objects.all()

    context = {
        "students": students,
        "groups": groups,
        "parents": parents,
    }

    return render(request, "students.html", context)


def handle_student_form(request):
    """
    Handle student creation and updates
    """
    try:
        # Get form data
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        birth_date = request.POST.get("birth_date")
        email = request.POST.get("email", "").strip()
        school = request.POST.get("school", "").strip()
        group_id = request.POST.get("group")
        allergies = request.POST.get("allergies", "").strip()
        gdpr_signed = request.POST.get("gdpr_signed") == "on"
        active = request.POST.get("active") == "on"
        parent_ids = request.POST.getlist("parents")

        # Validation
        if not first_name or not last_name:
            messages.error(request, "El nombre y apellidos son obligatorios.")
            return redirect("students_list")

        if not birth_date:
            messages.error(request, "La fecha de nacimiento es obligatoria.")
            return redirect("students_list")

        if not group_id:
            messages.error(request, "Debe seleccionar un grupo.")
            return redirect("students_list")

        if not parent_ids:
            messages.error(request, "Debe seleccionar al menos un padre/tutor.")
            return redirect("students_list")

        # Get the group
        try:
            group = Group.objects.get(id=group_id, active=True)
        except Group.DoesNotExist:
            messages.error(request, "El grupo seleccionado no existe.")
            return redirect("students_list")

        # Get parents
        parents = Parent.objects.filter(id__in=parent_ids)
        if len(parents) != len(parent_ids):
            messages.error(request, "Algunos padres seleccionados no existen.")
            return redirect("students_list")

        # Use transaction to ensure data consistency
        with transaction.atomic():
            # Check if this is an update (student_id present) or create
            student_id = request.POST.get("student_id")

            if student_id:  # Update existing student
                try:
                    student = Student.objects.get(id=student_id)

                    # Update student fields
                    student.first_name = first_name
                    student.last_name = last_name
                    student.birth_date = birth_date
                    student.email = email if email else ""
                    student.school = school if school else ""
                    student.group = group
                    student.allergies = allergies if allergies else ""
                    student.gdpr_signed = gdpr_signed
                    student.active = active

                    student.full_clean()  # Validate the model
                    student.save()

                    # Update parent relationships
                    student.parents.clear()  # Remove all current relationships
                    student.parents.set(parents)  # Set new relationships

                    messages.success(
                        request,
                        f"Estudiante {student.full_name} actualizado correctamente.",
                    )

                except Student.DoesNotExist:
                    messages.error(request, "El estudiante a actualizar no existe.")
                    return redirect("students_list")

            else:  # Create new student
                student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    email=email if email else "",
                    school=school if school else "",
                    group=group,
                    allergies=allergies if allergies else "",
                    gdpr_signed=gdpr_signed,
                    active=active,
                )

                student.full_clean()  # Validate the model
                student.save()

                # Add parent relationships
                student.parents.set(parents)

                messages.success(
                    request, f"Estudiante {student.full_name} creado correctamente."
                )

        return redirect("students_list")

    except ValidationError as e:
        if hasattr(e, "message_dict"):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
        else:
            messages.error(request, f"Error de validación: {e.message}")
        return redirect("students_list")

    except Exception as e:
        messages.error(request, f"Error al procesar el formulario: {str(e)}")
        return redirect("students_list")


def student_detail(request, student_id):
    """
    API endpoint to get student details for editing
    """
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        student = get_object_or_404(
            Student.objects.select_related("group").prefetch_related("parents"),
            id=student_id,
        )

        # Prepare student data
        student_data = {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "birth_date": student.birth_date.strftime("%Y-%m-%d"),
            "email": student.email,
            "school": student.school,
            "group": student.group.id,
            "allergies": student.allergies,
            "gdpr_signed": student.gdpr_signed,
            "active": student.active,
            "parents": [parent.id for parent in student.parents.all()],
        }

        return JsonResponse(student_data)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


def update_student(request, student_id):
    """
    Maneja la edición de un estudiante:
    - GET: devuelve datos en JSON para rellenar el modal (AJAX).
    - POST: actualiza datos usando handle_student_form y redirige a /students.
    """
    if request.method == "GET":
        student = get_object_or_404(
            Student.objects.select_related("group").prefetch_related("parents"),
            id=student_id,
        )

        data = {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "birth_date": student.birth_date.strftime("%Y-%m-%d"),
            "email": student.email,
            "school": student.school,
            "group": student.group.id if student.group else None,
            "allergies": student.allergies,
            "gdpr_signed": student.gdpr_signed,
            "active": student.active,
            "parents": list(student.parents.values_list("id", flat=True)),
        }
        return JsonResponse(data)

    elif request.method == "POST":
        request.POST = request.POST.copy()
        request.POST["student_id"] = student_id
        return handle_student_form(request)

    return JsonResponse({"error": "Method not allowed"}, status=405)


def payments_list(request):
    """
    Main payments list view with pagination
    Shows active payments only (not deactivated ones)
    """
    # Get all active payments ordered by most recent first
    payments_queryset = Payment.objects.select_related(
        "student", "parent", "enrollment", "enrollment__enrollment_type"
    ).order_by("-due_date", "-created_at")

    # Add search functionality
    search_query = request.GET.get("search", "")
    if search_query:
        payments_queryset = payments_queryset.filter(
            Q(student__first_name__icontains=search_query)
            | Q(student__last_name__icontains=search_query)
            | Q(parent__first_name__icontains=search_query)
            | Q(parent__last_name__icontains=search_query)
            | Q(concept__icontains=search_query)
            | Q(reference_number__icontains=search_query)
        )

    # Monthly payment totals
    today = date.today()
    current_month = today.month
    current_year = today.year

    # Expected: all payments due this month
    expected_qs = Payment.objects.filter(
        due_date__month=current_month,
        due_date__year=current_year,
    )
    expected_payments_total = expected_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    expected_payments_count = expected_qs.count()

    # Completed: payments completed this month
    completed_qs = Payment.objects.filter(
        payment_status="completed",
        payment_date__month=current_month,
        payment_date__year=current_year,
    )
    completed_payments_total = completed_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    completed_payments_count = completed_qs.count()

    # Pending: not-yet-completed payments
    pending_qs = Payment.objects.filter(
        payment_status="pending",
    )
    pending_payments_total = pending_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    pending_payments_count = pending_qs.count()

    # Overdue: pending payments past due date
    overdue_qs = Payment.objects.filter(
        payment_status="pending",
        due_date__lt=today,
    )
    overdue_payments_total = overdue_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
    overdue_payments_count = overdue_qs.count()

    # Load up to 1000 payments for frontend filtering/pagination
    all_payments_list = list(payments_queryset[:1000])

    context = {
        "payments_list": all_payments_list,
        "total_count": payments_queryset.count(),
        "search_query": search_query,
        "expected_payments_total": expected_payments_total,
        "expected_payments_count": expected_payments_count,
        "completed_payments_total": completed_payments_total,
        "completed_payments_count": completed_payments_count,
        "pending_payments_total": pending_payments_total,
        "pending_payments_count": pending_payments_count,
        "overdue_payments_total": overdue_payments_total,
        "overdue_payments_count": overdue_payments_count,
        "payment_method_choices": constants.PAYMENT_METHOD_CHOICES,
    }

    return render(request, "payments/payments_list.html", context)


@require_http_methods(["GET", "POST"])
def create_payment(request):
    """
    Create new payment
    """
    if request.method == "POST":
        try:
            # Get form data
            student_id = request.POST.get("student_id")
            parent_id = request.POST.get("parent_id")

            # Validate student and parent exist
            student = get_object_or_404(Student, id=student_id)
            parent = get_object_or_404(Parent, id=parent_id)

            # Validate relationship
            if not student.parents.filter(id=parent_id).exists():
                messages.error(
                    request,
                    "El padre/tutor seleccionado no está asociado con este estudiante.",
                )
                return redirect("payments_list")

            # Get enrollment if exists
            enrollment = student.enrollments.first()

            # Create payment
            print("Se crea pago")
            payment = Payment.objects.create(
                student=student,
                parent=parent,
                enrollment=enrollment,
                payment_type=request.POST.get("payment_type"),
                payment_method=request.POST.get("payment_method"),
                amount=Decimal(request.POST.get("amount")),
                currency=request.POST.get("currency", "EUR"),
                payment_status=request.POST.get("payment_status", "pending"),
                due_date=request.POST.get("due_date"),
                payment_date=request.POST.get("payment_date") or None,
                concept=request.POST.get("concept"),
                reference_number=request.POST.get("reference_number", ""),
                observations=request.POST.get("observations", ""),
            )
            print("Terminado de crear pago")
            messages.success(
                request, f"Pago creado exitosamente para {student.full_name}."
            )
            print("Se redirecciona!")
            return redirect("payments_list")

        except Exception as e:
            messages.error(request, f"Error al crear el pago: {str(e)}")
            return redirect("payments_list")

    return render(request, "payments/payment_create.html", {})


def payment_detail(request, payment_id):
    """
    Get payment details as JSON for editing
    """
    payment = get_object_or_404(Payment, id=payment_id)

    data = {
        "id": payment.id,
        "student": {
            "id": payment.student.id,
            "full_name": payment.student.full_name,
            "school": payment.student.school or "",
        },
        "parent": {
            "id": payment.parent.id,
            "full_name": payment.parent.full_name,
            "email": payment.parent.email,
        },
        "enrollment": (
            {
                "id": payment.enrollment.id if payment.enrollment else None,
                "enrollment_type": (
                    payment.enrollment.enrollment_type.display_name
                    if payment.enrollment
                    else None
                ),
            }
            if payment.enrollment
            else None
        ),
        "payment_type": payment.payment_type,
        "payment_method": payment.payment_method,
        "amount": str(payment.amount),
        "currency": payment.currency,
        "payment_status": payment.payment_status,
        "due_date": payment.due_date.isoformat() if payment.due_date else None,
        "payment_date": (
            payment.payment_date.isoformat() if payment.payment_date else None
        ),
        "concept": payment.concept,
        "reference_number": payment.reference_number,
        "observations": payment.observations,
        "is_overdue": payment.is_overdue,
        "days_overdue": payment.days_overdue if payment.is_overdue else 0,
    }

    return JsonResponse(data)


@require_http_methods(["POST"])
def update_payment(request, payment_id):
    """
    Update existing payment
    """
    payment = get_object_or_404(Payment, id=payment_id)

    try:
        # Get form data
        student_id = request.POST.get("student_id")
        parent_id = request.POST.get("parent_id")

        # Validate student and parent exist
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)

        # Validate relationship
        if not student.parents.filter(id=parent_id).exists():
            messages.error(
                request,
                "El padre/tutor seleccionado no está asociado con este estudiante.",
            )
            return redirect("payments_list")

        # Update payment fields
        payment.student = student
        payment.parent = parent
        payment.payment_type = request.POST.get("payment_type")
        payment.payment_method = request.POST.get("payment_method")
        payment.amount = Decimal(request.POST.get("amount"))
        payment.currency = request.POST.get("currency", "EUR")
        payment.payment_status = request.POST.get("payment_status")
        payment.due_date = request.POST.get("due_date")
        payment.payment_date = request.POST.get("payment_date") or None
        payment.concept = request.POST.get("concept")
        payment.reference_number = request.POST.get("reference_number", "")
        payment.observations = request.POST.get("observations", "")

        payment.save()

        messages.success(
            request, f"Pago actualizado exitosamente para {student.full_name}."
        )

    except Exception as e:
        messages.error(request, f"Error al actualizar el pago: {str(e)}")

    return redirect("payments_list")


def payment_detail_view(request, payment_id):
    """
    Detailed view of a payment (read-only)
    """
    payment = get_object_or_404(Payment, id=payment_id)

    context = {
        "payment": payment,
    }

    return render(request, "payments/payment_detail.html", context)


# Soft delete!
@require_http_methods(["POST"])
def deactivate_payment(request, payment_id):
    """
    Soft delete - deactivate payment instead of deleting
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id, active=True)
        payment.active = False  # Soft delete
        payment.save()

        return JsonResponse(
            {"success": True, "message": f"Pago desactivado exitosamente."}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error al desactivar el pago: {str(e)}"},
            status=400,
        )


# API Endpoints for AJAX functionality (Student)


def search_students(request):
    """
    AJAX endpoint to search students
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    students = Student.objects.filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(school__icontains=query),
        active=True,
    ).select_related("group")[
        :10
    ]  # Limit to 10 results

    results = []
    for student in students:
        results.append(
            {
                "id": student.id,
                "full_name": student.full_name,
                "school": student.school or "",
                "group": student.group.group_name if student.group else "",
                "age": student.age,
            }
        )

    return JsonResponse({"results": results})


def search_parents(request):
    """
    AJAX endpoint to search parents
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    parents = Parent.objects.filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
    )[
        :10
    ]  # Limit to 10 results

    results = []
    for parent in parents:
        results.append(
            {
                "id": parent.id,
                "full_name": parent.full_name,
                "email": parent.email,
                "phone": parent.phone or "",
            }
        )

    return JsonResponse({"results": results})


@require_http_methods(["POST"])
def validate_student_parent(request):
    """
    AJAX endpoint to validate student-parent relationship
    """
    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
        parent_id = data.get("parent_id")

        if not student_id or not parent_id:
            return JsonResponse(
                {"valid": False, "message": "Missing student or parent ID"}
            )

        # Check if relationship exists
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)

        is_valid = student.parents.filter(id=parent_id).exists()

        response_data = {
            "valid": is_valid,
            "message": "Valid relationship" if is_valid else "Invalid relationship",
        }

        # If valid, include enrollment info
        if is_valid:
            active_enrollment = student.enrollments.filter(status="active").first()
            if active_enrollment:
                response_data["enrollment"] = {
                    "id": active_enrollment.id,
                    "enrollment_type": active_enrollment.enrollment_type.display_name,
                    "remaining_amount": str(active_enrollment.remaining_amount),
                    "schedule_type": active_enrollment.get_schedule_type_display(),
                    "is_paid": active_enrollment.is_paid,
                }

        return JsonResponse(response_data)

    except json.JSONDecodeError:
        return JsonResponse(
            {"valid": False, "message": "Invalid JSON data"}, status=400
        )
    except Exception as e:
        return JsonResponse({"valid": False, "message": str(e)}, status=400)


# API Endpoints for AJAX functionality (Payment)


def search_payments(request):
    """
    AJAX endpoint to search payments
    """
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    payments = (
        Payment.objects.filter(
            Q(student__first_name__icontains=query)
            | Q(student__last_name__icontains=query)
            | Q(parent__first_name__icontains=query)
            | Q(parent__last_name__icontains=query)
            | Q(concept__icontains=query)
            | Q(reference_number__icontains=query)
        )
        .select_related("student", "parent", "enrollment")
        .order_by("-created_at")[:10]
    )

    results = []
    for payment in payments:
        results.append(
            {
                "id": payment.id,
                "student_name": payment.student.full_name,
                "parent_name": payment.parent.full_name,
                "amount": str(payment.amount),
                "currency": payment.currency,
                "payment_type": payment.get_payment_type_display(),
                "payment_status": payment.get_payment_status_display(),
                "due_date": (
                    payment.due_date.strftime("%Y-%m-%d") if payment.due_date else ""
                ),
                "payment_date": (
                    payment.payment_date.strftime("%Y-%m-%d")
                    if payment.payment_date
                    else ""
                ),
                "concept": payment.concept,
                "reference_number": payment.reference_number,
            }
        )

    return JsonResponse({"results": results})


@require_http_methods(["POST"])
def update_payment(request, payment_id):
    """
    AJAX endpoint to update existing payment
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)

        # Parse data
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        # Update fields
        if "student_id" in data:
            student = get_object_or_404(Student, id=data["student_id"])
            payment.student = student
        if "parent_id" in data:
            parent = get_object_or_404(Parent, id=data["parent_id"])
            payment.parent = parent
        if payment.student_id and payment.parent_id and not payment.student.parents.filter(
            id=payment.parent_id
        ).exists():
            raise ValidationError(
                "El padre/tutor seleccionado no está asociado con este estudiante."
            )
        if "payment_type" in data:
            payment.payment_type = data["payment_type"]
        if "payment_method" in data:
            payment.payment_method = data["payment_method"]
        if "amount" in data:
            payment.amount = Decimal(data["amount"])
        if "currency" in data:
            payment.currency = data["currency"]
        if "payment_status" in data:
            payment.payment_status = data["payment_status"]
        if "due_date" in data:
            payment.due_date = parse_date_value(data["due_date"])
        if "payment_date" in data:
            payment.payment_date = parse_date_value(data["payment_date"])
        if "concept" in data:
            payment.concept = data["concept"]
        if "reference_number" in data:
            payment.reference_number = data["reference_number"]
        if "observations" in data:
            payment.observations = data["observations"]

        payment.save()

        if request.content_type != "application/json":
            messages.success(request, "Pago actualizado exitosamente.")
            return redirect("payments_list")

        return JsonResponse(
            {
                "success": True,
                "message": "Pago actualizado exitosamente.",
                "payment": {
                    "id": payment.id,
                    "payment_status": payment.get_payment_status_display(),
                    "amount": str(payment.amount),
                },
            }
        )

    except (InvalidOperation, ValidationError) as e:
        if request.content_type == "application/json":
            return JsonResponse(
                {"success": False, "error": str(e)},
                status=400,
            )
        messages.error(request, str(e))
        return redirect("payments_list")
    except Exception as e:
        if request.content_type == "application/json":
            return JsonResponse(
                {"success": False, "error": f"Error al actualizar el pago: {str(e)}"},
                status=500,
            )
        messages.error(request, f"Error al actualizar el pago: {str(e)}")
        return redirect("payments_list")


@require_http_methods(["POST"])
def delete_payment(request, payment_id):
    """
    AJAX endpoint to delete payment
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        student_name = payment.student.full_name

        payment.delete()

        return JsonResponse(
            {
                "success": True,
                "message": f"Pago de {student_name} eliminado exitosamente.",
            }
        )

    except Exception as e:
        print(f"ERROR deleting payment: {str(e)}")
        import traceback

        traceback.print_exc()

        return JsonResponse(
            {"success": False, "error": f"Error al eliminar el pago: {str(e)}"},
            status=500,
        )


@require_http_methods(["POST"])
def quick_complete_payment(request, payment_id):
    """
    AJAX endpoint to quickly complete a payment by setting its payment method.
    Expects JSON body: {"payment_method": "cash"|"transfer"|"credit_card"}
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        data = json.loads(request.body)
        payment_method = data.get("payment_method")

        if payment_method not in dict(constants.PAYMENT_METHOD_CHOICES):
            return JsonResponse(
                {"success": False, "error": "Método de pago no válido"},
                status=400,
            )

        payment.payment_method = payment_method
        payment.payment_status = "completed"
        payment.payment_date = date.today()
        payment.save()

        return JsonResponse({
            "success": True,
            "message": f"Pago de {payment.student.full_name} completado ({payment.get_payment_method_display()}).",
        })

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error al completar el pago: {str(e)}"},
            status=500,
        )


@require_http_methods(["POST"])
def update_enrollment_modality(request, student_id):
    """
    AJAX endpoint to change a student's payment modality (monthly/quarterly).
    Expects JSON body: {"payment_modality": "monthly"|"quarterly"}
    """
    try:
        student = get_object_or_404(Student, id=student_id)
        data = json.loads(request.body)
        modality = data.get("payment_modality")

        if modality not in dict(constants.PAYMENT_MODALITY_CHOICES):
            return JsonResponse(
                {"success": False, "error": "Modalidad de pago no válida"},
                status=400,
            )

        enrollment = student.enrollments.filter(status='active').first()
        if not enrollment:
            return JsonResponse(
                {"success": False, "error": "No tiene matrícula activa"},
                status=404,
            )

        enrollment.payment_modality = modality
        enrollment.save()

        return JsonResponse({
            "success": True,
            "message": f"Modalidad cambiada a {enrollment.get_payment_modality_display()}.",
            "payment_modality": modality,
            "payment_modality_display": enrollment.get_payment_modality_display(),
        })

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


@require_http_methods(["GET"])
def language_cheque_students(request):
    """
    API endpoint to fetch students with active language cheque (cheque idioma).
    These students need to be reported to the government monthly.
    """
    academic_year = current_academic_year()
    enrollments = Enrollment.objects.filter(
        status='active',
        academic_year=academic_year,
        has_language_cheque=True,
    ).select_related('student', 'student__group')

    students_data = []
    for enrollment in enrollments:
        s = enrollment.student
        parent = s.parents.first()
        students_data.append({
            'id': s.id,
            'full_name': s.full_name,
            'birth_date': s.birth_date.strftime('%Y-%m-%d'),
            'group': s.group.group_name if s.group else '',
            'parent_name': parent.full_name if parent else '',
            'parent_dni': parent.dni if parent else '',
            'schedule_type': enrollment.get_schedule_type_display(),
        })

    return JsonResponse({
        'success': True,
        'academic_year': academic_year,
        'count': len(students_data),
        'students': students_data,
    })


@require_http_methods(["GET"])
def get_payment_details(request, payment_id):
    """
    AJAX endpoint to get payment details
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)

        return JsonResponse(
            {
                "success": True,
                "payment": {
                    "id": payment.id,
                    "student_id": payment.student.id,
                    "student_name": payment.student.full_name,
                    "parent_id": payment.parent.id if payment.parent else None,
                    "parent_name": payment.parent.full_name if payment.parent else "",
                    "enrollment_id": (
                        payment.enrollment.id if payment.enrollment else None
                    ),
                    "payment_type": payment.payment_type,
                    "payment_method": payment.payment_method,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "payment_status": payment.payment_status,
                    "due_date": (
                        payment.due_date.strftime("%Y-%m-%d")
                        if payment.due_date
                        else ""
                    ),
                    "payment_date": (
                        payment.payment_date.strftime("%Y-%m-%d")
                        if payment.payment_date
                        else ""
                    ),
                    "concept": payment.concept,
                    "reference_number": payment.reference_number,
                    "observations": payment.observations,
                    "created_at": payment.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                },
            }
        )

    except Exception as e:
        return JsonResponse(
            {
                "success": False,
                "error": f"Error al obtener los detalles del pago: {str(e)}",
            },
            status=500,
        )


# Additional utility views


def payment_statistics(request):
    """
    Get payment statistics for dashboard
    """
    today = date.today()

    stats = {
        "total_payments": Payment.objects.filter(active=True).count(),
        "completed_payments": Payment.objects.filter(
            active=True, payment_status="completed"
        ).count(),
        "pending_payments": Payment.objects.filter(
            active=True, payment_status="pending"
        ).count(),
        "overdue_payments": Payment.objects.filter(
            active=True, payment_status="pending", due_date__lt=today
        ).count(),
        "total_amount_pending": Payment.objects.filter(
            active=True, payment_status="pending"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
        "total_amount_completed": Payment.objects.filter(
            active=True, payment_status="completed"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
    }

    return JsonResponse(stats)


def export_payments(request):
    """
    Export payments to CSV
    """
    import csv
    from django.http import HttpResponse

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pagos.csv"'

    writer = csv.writer(response)
    writer.writerow(
        [
            "ID",
            "Estudiante",
            "Padre/Tutor",
            "Concepto",
            "Cantidad",
            "Método",
            "Estado",
            "Fecha Vencimiento",
            "Fecha Pago",
            "Creado",
        ]
    )

    payments = (
        Payment.objects.filter(active=True)
        .select_related("student", "parent")
        .order_by("-created_at")
    )

    for payment in payments:
        writer.writerow(
            [
                payment.id,
                payment.student.full_name,
                payment.parent.full_name,
                payment.concept,
                payment.amount,
                payment.get_payment_method_display(),
                payment.get_payment_status_display(),
                payment.due_date.strftime("%d/%m/%Y") if payment.due_date else "",
                (
                    payment.payment_date.strftime("%d/%m/%Y")
                    if payment.payment_date
                    else ""
                ),
                payment.created_at.strftime("%d/%m/%Y %H:%M"),
            ]
        )

    return response


def export_database_excel(request):
    """Export Estudiantes, Matrículas and Pagos as a single .xlsx file."""
    from datetime import datetime
    from django.http import HttpResponse
    from .exports import build_database_workbook

    wb = build_database_workbook()
    today = datetime.now().strftime("%Y%m%d")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="five_a_day_{today}.xlsx"'
    wb.save(response)
    return response


# ============================================================================
# GESTIÓN - Site Configuration, Teachers & Groups Management
# ============================================================================


def gestion_view(request):
    """
    Vista principal de gestión con configuración de precios, profesores y grupos.
    """
    from .models import SiteConfiguration, Teacher, Group

    config = SiteConfiguration.get_config()
    teachers = Teacher.objects.filter(active=True).order_by("first_name", "last_name")
    groups = (
        Group.objects.filter(active=True)
        .select_related("teacher")
        .order_by("group_name")
    )

    context = {
        "config": config,
        "teachers": teachers,
        "groups": groups,
    }
    return render(request, "management.html", context)


@require_http_methods(["POST"])
def update_site_config(request):
    """
    API para actualizar la configuración de precios del sitio.
    """
    from .models import SiteConfiguration

    try:
        data = json.loads(request.body)
        config = SiteConfiguration.get_config()

        # Actualizar precios de matrícula
        if "children_enrollment_fee" in data:
            config.children_enrollment_fee = Decimal(
                str(data["children_enrollment_fee"])
            )
        if "adult_enrollment_fee" in data:
            config.adult_enrollment_fee = Decimal(str(data["adult_enrollment_fee"]))

        # Actualizar mensualidades
        if "full_time_monthly_fee" in data:
            config.full_time_monthly_fee = Decimal(str(data["full_time_monthly_fee"]))
        if "part_time_monthly_fee" in data:
            config.part_time_monthly_fee = Decimal(str(data["part_time_monthly_fee"]))
        if "adult_group_monthly_fee" in data:
            config.adult_group_monthly_fee = Decimal(
                str(data["adult_group_monthly_fee"])
            )

        # Actualizar descuentos
        for field in [
            "language_cheque_discount",
            "quarterly_enrollment_discount",
            "old_student_discount",
            "june_discount",
            "full_year_bonus",
            "sibling_discount",
            "half_month_discount",
            "one_week_discount",
            "three_week_discount",
        ]:
            if field in data:
                setattr(config, field, Decimal(str(data[field])))

        config.save()

        return JsonResponse(
            {"success": True, "message": "Configuración actualizada correctamente"}
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_http_methods(["POST"])
def create_teacher(request):
    """
    API para crear un nuevo profesor.
    """
    from .models import Teacher

    try:
        data = json.loads(request.body)

        # Validar campos requeridos
        required_fields = ["first_name", "last_name", "email"]
        for field in required_fields:
            if not data.get(field):
                return JsonResponse(
                    {"success": False, "message": f"El campo {field} es requerido"},
                    status=400,
                )

        # Verificar email único
        if Teacher.objects.filter(email=data["email"]).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un profesor con ese email"},
                status=400,
            )

        teacher = Teacher.objects.create(
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data.get("phone", ""),
            active=True,
            admin=data.get("admin", False),
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Profesor creado correctamente",
                "teacher": {
                    "id": teacher.id,
                    "full_name": teacher.full_name,
                    "email": teacher.email,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_http_methods(["POST"])
def create_group(request):
    """
    API para crear un nuevo grupo.
    """
    from .models import Group, Teacher

    try:
        data = json.loads(request.body)

        # Validar campos requeridos
        if not data.get("group_name"):
            return JsonResponse(
                {"success": False, "message": "El nombre del grupo es requerido"},
                status=400,
            )

        if not data.get("teacher_id"):
            return JsonResponse(
                {"success": False, "message": "El profesor es requerido"}, status=400
            )

        # Verificar nombre único
        if Group.objects.filter(group_name=data["group_name"]).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un grupo con ese nombre"},
                status=400,
            )

        # Verificar que el profesor existe
        try:
            teacher = Teacher.objects.get(id=data["teacher_id"], active=True)
        except Teacher.DoesNotExist:
            return JsonResponse(
                {"success": False, "message": "El profesor seleccionado no existe"},
                status=400,
            )

        group = Group.objects.create(
            group_name=data["group_name"],
            color=data.get("color", "#6366f1"),
            teacher=teacher,
            active=True,
        )

        return JsonResponse(
            {
                "success": True,
                "message": "Grupo creado correctamente",
                "group": {
                    "id": group.id,
                    "group_name": group.group_name,
                    "teacher_name": teacher.full_name,
                },
            }
        )
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


def api_get_teachers(request):
    """
    API para obtener lista de profesores activos (para select de grupos).
    """
    from .models import Teacher

    teachers = Teacher.objects.filter(active=True).order_by("first_name", "last_name")
    data = [{"id": t.id, "full_name": t.full_name, "email": t.email} for t in teachers]
    return JsonResponse({"teachers": data})


# ============================================================================
# FUN FRIDAY - Formulario de envío masivo
# ============================================================================


def fun_friday_form(request):
    """
    Vista para el formulario de Fun Friday.
    GET: Muestra el formulario con valores por defecto
    POST: Valida HTML y envía emails a todos los padres con estudiantes activos
    """
    from datetime import date, timedelta
    from .models import Parent, Student
    from .email import send_fun_friday_email
    import html.parser

    # Calcular próximo viernes
    today = date.today()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7  # Si hoy es viernes, el próximo viernes
    next_friday = today + timedelta(days=days_until_friday)

    # Contar padres con estudiantes activos (excluir adultos)
    parent_count = Parent.objects.filter(children__active=True, children__is_adult=False).distinct().count()

    # HTML por defecto de ejemplo
    default_html = """<strong>🎉 ¡SESIÓN DE MANUALIDADES!</strong>
<br><br>
Esta semana haremos manualidades creativas con materiales reciclados.
<br><br>
<em>Los niños deben traer:</em>
<ul>
    <li>Una camiseta vieja</li>
    <li>Tijeras de punta redonda</li>
</ul>
<br>
¡Os esperamos! 🎨"""

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _event_date_str = request.POST.get('event_date', next_friday.isoformat())
            _start_time = request.POST.get('start_time', '17:00')
            _end_time = request.POST.get('end_time', '18:30')
            _meeting_point = request.POST.get('meeting_point', '')
            _activity = request.POST.get('activity_description', default_html)
            try:
                _ed = date.fromisoformat(_event_date_str)
            except (ValueError, TypeError):
                _ed = next_friday
            try:
                _min_age = int(request.POST.get('min_age', 5))
                _max_age = int(request.POST.get('max_age', 12))
            except (ValueError, TypeError):
                _min_age, _max_age = 5, 12
            _ctx = {
                'day_name': DIAS_ES[_ed.weekday()],
                'day_number': _ed.day,
                'month': MESES_ES[_ed.month - 1],
                'start_time': _start_time,
                'end_time': _end_time,
                'activity_description': _activity,
                'meeting_point': _meeting_point,
                'minimum_age': _min_age,
                'maximum_age': _max_age,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/fun_friday.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='fun_friday',
                recipients=_recipients,
                subject=f'[TEST] 🎉 Fun Friday - {_ctx["day_name"].capitalize()} {_ctx["day_number"]} de {_ctx["month"]}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        # Obtener datos del formulario
        event_date_str = request.POST.get("event_date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        meeting_point = request.POST.get("meeting_point", "")
        min_age = request.POST.get("min_age")
        max_age = request.POST.get("max_age")
        activity_description = request.POST.get("activity_description", "")

        # Validar campos requeridos
        if not all(
            [
                event_date_str,
                start_time,
                end_time,
                min_age,
                max_age,
                activity_description,
            ]
        ):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description or default_html,
                },
            )

        # Validar HTML
        try:
            parser = html.parser.HTMLParser()
            parser.feed(activity_description)
        except Exception as e:
            messages.error(request, f"❌ HTML inválido: {str(e)}")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        # Parsear fecha
        try:
            event_date = date.fromisoformat(event_date_str)
        except ValueError:
            messages.error(request, "❌ Fecha inválida")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        # Validar edades
        try:
            min_age_int = int(min_age)
            max_age_int = int(max_age)
            if min_age_int > max_age_int:
                raise ValueError("Edad mínima mayor que máxima")
        except ValueError as e:
            messages.error(request, f"❌ Error en rango de edades: {str(e)}")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        day_name = DIAS_ES[event_date.weekday()]
        month_name = MESES_ES[event_date.month - 1]

        # Obtener emails de padres con estudiantes activos
        parents = Parent.objects.filter(children__active=True).distinct()

        parent_emails = [p.email for p in parents if p.email]

        if not parent_emails:
            messages.warning(request, "⚠️ No hay padres con email para enviar")
            return redirect("home")

        # Enviar emails
        success_count = 0
        error_count = 0

        for email in parent_emails:
            try:
                result = send_fun_friday_email(
                    recipients=email,
                    day_name=day_name,
                    day_number=event_date.day,
                    month=month_name,
                    start_time=start_time,
                    end_time=end_time,
                    activity_description=activity_description,
                    minimum_age=min_age_int,
                    maximum_age=max_age_int,
                    meeting_point=meeting_point if meeting_point else None,
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1

        if success_count > 0:
            messages.success(
                request, f"✅ Fun Friday enviado a {success_count} padre(s)"
            )
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")

        return redirect("home")

    # GET - Mostrar formulario con email preview
    email_html = render_to_string('emails/fun_friday.html', {
        'day_name': DIAS_ES[next_friday.weekday()],
        'day_number': next_friday.day,
        'month': MESES_ES[next_friday.month - 1],
        'start_time': '17:00',
        'end_time': '18:30',
        'activity_description': default_html,
        'meeting_point': 'En la puerta principal del centro',
        'minimum_age': 5,
        'maximum_age': 12,
    })
    return render(
        request,
        "apps/fun_friday_form.html",
        {
            "next_friday": next_friday.isoformat(),
            "parent_count": parent_count,
            "default_html": default_html,
            "email_html": email_html,
        },
    )


# ============================================================================
# RECORDATORIO DE PAGO - Formulario de envío
# ============================================================================


def payment_reminder_form(request):
    """
    Vista para enviar recordatorios de pago mensual/trimestral.
    GET: Muestra formulario con valores por defecto
    POST: Envía recordatorio a todos los padres con estudiantes activos
    """
    from .models import Parent
    from .email import send_payment_reminder_email

    today = date.today()
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    # Defaults: pago del 1 al 5 del mes actual
    default_start = today.replace(day=1)
    try:
        default_end = today.replace(day=5)
    except ValueError:
        default_end = today.replace(day=28)

    current_month = MESES_ES[today.month - 1]

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _start_str = request.POST.get('payment_start_date', default_start.isoformat())
            _end_str = request.POST.get('payment_end_date', default_end.isoformat())
            _month = request.POST.get('month', current_month)
            _iban = request.POST.get('iban_number', 'ES00 0000 0000 0000 0000 0000')
            _bizum = request.POST.get('telephone_number_bizum', '600 000 000')
            _cheque = request.POST.get('reduced_price_cheque_idioma', '34€')
            try:
                _sd = date.fromisoformat(_start_str)
                _ed = date.fromisoformat(_end_str)
            except (ValueError, TypeError):
                _sd, _ed = default_start, default_end
            _ctx = {
                'payment_start_day_name': DIAS_ES[_sd.weekday()],
                'payment_start_day_number': _sd.day,
                'payment_end_day_name': DIAS_ES[_ed.weekday()],
                'payment_end_day_number': _ed.day,
                'month': _month,
                'iban_number': _iban,
                'reduced_price_cheque_idioma': _cheque,
                'telephone_number_bizum': _bizum,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/recordatorio_pago_mensual_trimestral.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='recordatorio_pago_mensual_trimestral',
                recipients=_recipients,
                subject=f'[TEST] 💰 Recordatorio de Pago - {_month.title()}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        payment_start_date_str = request.POST.get("payment_start_date")
        payment_end_date_str = request.POST.get("payment_end_date")
        month = request.POST.get("month", current_month)
        iban_number = request.POST.get("iban_number", "")
        telephone_number_bizum = request.POST.get("telephone_number_bizum", "")
        reduced_price_cheque_idioma = request.POST.get("reduced_price_cheque_idioma", "34€")

        if not all([payment_start_date_str, payment_end_date_str, iban_number, telephone_number_bizum]):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
        else:
            try:
                start_date = date.fromisoformat(payment_start_date_str)
                end_date = date.fromisoformat(payment_end_date_str)
            except ValueError:
                messages.error(request, "❌ Fecha inválida")
                return redirect("payment_reminder_form")

            parents = Parent.objects.filter(children__active=True).distinct()
            parent_emails = [p.email for p in parents if p.email]

            if not parent_emails:
                messages.warning(request, "⚠️ No hay padres con email para enviar")
                return redirect("apps")

            success_count = 0
            error_count = 0
            for email_addr in parent_emails:
                try:
                    result = send_payment_reminder_email(
                        recipients=email_addr,
                        payment_start_day_name=DIAS_ES[start_date.weekday()],
                        payment_start_day_number=start_date.day,
                        payment_end_day_name=DIAS_ES[end_date.weekday()],
                        payment_end_day_number=end_date.day,
                        month=month,
                        iban_number=iban_number,
                        reduced_price_cheque_idioma=reduced_price_cheque_idioma,
                        telephone_number_bizum=telephone_number_bizum,
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

            if success_count > 0:
                messages.success(request, f"✅ Recordatorio enviado a {success_count} padre(s)")
            if error_count > 0:
                messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
            return redirect("apps")

    email_html = render_to_string('emails/recordatorio_pago_mensual_trimestral.html', {
        'payment_start_day_name': DIAS_ES[default_start.weekday()],
        'payment_start_day_number': default_start.day,
        'payment_end_day_name': DIAS_ES[default_end.weekday()],
        'payment_end_day_number': default_end.day,
        'month': current_month,
        'iban_number': 'ES00 0000 0000 0000 0000 0000',
        'reduced_price_cheque_idioma': '34€',
        'telephone_number_bizum': '600 000 000',
    })
    return render(request, "apps/payment_reminder_form.html", {
        "parent_count": parent_count,
        "default_start_date": default_start.isoformat(),
        "default_end_date": default_end.isoformat(),
        "months": MESES_ES,
        "current_month": current_month,
        "default_iban": "",
        "default_bizum": "",
        "default_cheque_price": "34€",
        "email_html": email_html,
    })


# ============================================================================
# CIERRE POR VACACIONES - Formulario de envío
# ============================================================================


def vacation_closure_form(request):
    """
    Vista para enviar avisos de cierre por vacaciones.
    GET: Muestra formulario
    POST: Envía aviso a todos los padres con estudiantes activos
    """
    from .models import Parent
    from .email import send_vacation_closure_email

    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            from datetime import timedelta
            _cs_str = request.POST.get('closure_start_date', '')
            _ce_str = request.POST.get('closure_end_date', '')
            _r_str = request.POST.get('reopening_date', '')
            _reason = request.POST.get('closure_reason', 'Vacaciones')
            try:
                _cs = date.fromisoformat(_cs_str)
                _ce = date.fromisoformat(_ce_str)
                _ro = date.fromisoformat(_r_str)
            except (ValueError, TypeError):
                _cs = date.today()
                _ce = _cs + timedelta(days=7)
                _ro = _ce + timedelta(days=3)
            _ctx = {
                'start_closure_day_name': DIAS_ES[_cs.weekday()],
                'start_closure_day_number': _cs.day,
                'end_closure_day_name': DIAS_ES[_ce.weekday()],
                'end_closure_day_number': _ce.day,
                'month_closure': MESES_ES[_cs.month - 1],
                'closure_reason': _reason,
                'reopening_day_name': DIAS_ES[_ro.weekday()],
                'reopening_day_number': _ro.day,
                'month_reopening': MESES_ES[_ro.month - 1],
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/recordatorio_cierre_vacaciones.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='recordatorio_cierre_vacaciones',
                recipients=_recipients,
                subject=f'[TEST] 🏖️ Cierre por {_reason} - Five a Day',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        closure_start_str = request.POST.get("closure_start_date")
        closure_end_str = request.POST.get("closure_end_date")
        closure_reason = request.POST.get("closure_reason", "")
        reopening_str = request.POST.get("reopening_date")

        if not all([closure_start_str, closure_end_str, closure_reason, reopening_str]):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
        else:
            try:
                closure_start = date.fromisoformat(closure_start_str)
                closure_end = date.fromisoformat(closure_end_str)
                reopening = date.fromisoformat(reopening_str)
            except ValueError:
                messages.error(request, "❌ Fecha inválida")
                return redirect("vacation_closure_form")

            parents = Parent.objects.filter(children__active=True).distinct()
            parent_emails = [p.email for p in parents if p.email]

            if not parent_emails:
                messages.warning(request, "⚠️ No hay padres con email para enviar")
                return redirect("apps")

            success_count = 0
            error_count = 0
            for email_addr in parent_emails:
                try:
                    result = send_vacation_closure_email(
                        recipients=email_addr,
                        start_closure_day_name=DIAS_ES[closure_start.weekday()],
                        start_closure_day_number=closure_start.day,
                        end_closure_day_name=DIAS_ES[closure_end.weekday()],
                        end_closure_day_number=closure_end.day,
                        month_closure=MESES_ES[closure_start.month - 1],
                        closure_reason=closure_reason,
                        reopening_day_name=DIAS_ES[reopening.weekday()],
                        reopening_day_number=reopening.day,
                        month_reopening=MESES_ES[reopening.month - 1],
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

            if success_count > 0:
                messages.success(request, f"✅ Aviso de cierre enviado a {success_count} padre(s)")
            if error_count > 0:
                messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
            return redirect("apps")

    email_html = render_to_string('emails/recordatorio_cierre_vacaciones.html', {
        'start_closure_day_name': 'lunes',
        'start_closure_day_number': 23,
        'end_closure_day_name': 'viernes',
        'end_closure_day_number': 3,
        'month_closure': 'diciembre',
        'closure_reason': 'Navidad',
        'reopening_day_name': 'lunes',
        'reopening_day_number': 8,
        'month_reopening': 'enero',
    })
    return render(request, "apps/vacation_closure_form.html", {
        "parent_count": parent_count,
        "email_html": email_html,
    })


# ============================================================================
# CERTIFICADO RENTA - Generación y envío
# ============================================================================


def tax_certificate_form(request):
    """
    Vista para generar y enviar certificados fiscales.
    GET: Muestra formulario con año por defecto
    POST: Genera y envía certificados a todos los padres con pagos
    """
    from .models import Parent, Payment
    from .email import send_all_tax_certificates

    today = date.today()
    default_year = today.year - 1  # Año fiscal anterior

    parents_with_payments = Parent.objects.filter(
        payments__payment_status='completed',
        payments__payment_date__year=default_year
    ).distinct().count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _year = int(request.POST.get('year', default_year))
            _ctx = {'year': _year, 'parent_name': 'Nombre del padre'}
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/certificado_renta.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='certificado_renta',
                recipients=_recipients,
                subject=f'[TEST] 📋 Certificado de Renta {_year} - Five a Day',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        year = int(request.POST.get("year", default_year))
        results = send_all_tax_certificates(year)

        if results['sent'] > 0:
            messages.success(request, f"✅ Certificados enviados a {results['sent']} padre(s)")
        if results.get('skipped', 0) > 0:
            messages.info(request, f"ℹ️ {results['skipped']} padre(s) omitidos (sin email)")
        if results.get('failed', 0) > 0:
            messages.warning(request, f"⚠️ {results['failed']} certificado(s) fallaron")
        return redirect("apps")

    email_html = render_to_string('emails/certificado_renta.html', {
        'year': default_year,
        'parent_name': 'Nombre del padre',
    })
    return render(request, "apps/tax_certificate_form.html", {
        "default_year": default_year,
        "parents_with_payments": parents_with_payments,
        "email_html": email_html,
    })


# ============================================================================
# INFORME MENSUAL - Formulario de envío
# ============================================================================


def monthly_report_form(request):
    """
    Vista para enviar informes mensuales a los padres.
    GET: Muestra formulario con mes/año actual
    POST: Envía informes personalizados a cada padre
    """
    from .models import Parent, Student, Group
    from .email import send_monthly_report

    today = date.today()
    current_month = MESES_ES[today.month - 1]
    parent_count = Parent.objects.filter(children__active=True).distinct().count()
    total_students = Student.objects.filter(active=True).count()
    total_groups = Group.objects.filter(active=True).count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _month = request.POST.get('month', current_month)
            try:
                _year = int(request.POST.get('year', today.year))
            except (ValueError, TypeError):
                _year = today.year
            _ctx = {
                'month': _month,
                'year': _year,
                'parent_name': 'Nombre del padre',
                'students': [{'name': 'Alumno Ejemplo', 'group': 'Grupo A'}],
                'total_students': 1,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/monthly_report.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='monthly_report',
                recipients=_recipients,
                subject=f'[TEST] 📊 Informe Mensual - {_month.title()} {_year}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        month = request.POST.get("month", current_month)
        year = int(request.POST.get("year", today.year))

        parents = Parent.objects.filter(
            children__active=True
        ).distinct().prefetch_related('children__group')

        success_count = 0
        error_count = 0
        for parent in parents:
            if not parent.email:
                continue
            students_data = [
                {'name': s.full_name, 'group': s.group.group_name if s.group else 'Sin grupo'}
                for s in parent.children.filter(active=True)
            ]
            try:
                result = send_monthly_report(
                    recipient=parent.email,
                    report_data={
                        'month': month,
                        'year': year,
                        'parent_name': parent.full_name,
                        'students': students_data,
                        'total_students': len(students_data),
                    }
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            messages.success(request, f"✅ Informes enviados a {success_count} padre(s)")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} informe(s) no pudieron enviarse")
        return redirect("apps")

    email_html = render_to_string('emails/monthly_report.html', {
        'month': current_month,
        'year': today.year,
        'parent_name': 'Nombre del padre',
        'students': [{'name': 'Alumno Ejemplo', 'group': 'Grupo A'}],
        'total_students': 1,
    })
    return render(request, "apps/monthly_report_form.html", {
        "months": MESES_ES,
        "current_month": current_month,
        "current_year": today.year,
        "parent_count": parent_count,
        "total_students": total_students,
        "total_groups": total_groups,
        "email_html": email_html,
    })


# ============================================================================
# BIENVENIDA - Email de alta de estudiante
# ============================================================================


def welcome_form(request):
    """Merged into enrollment_form — redirect all traffic there."""
    return redirect("enrollment_form")


# ============================================================================
# CUMPLEAÑOS - Gestión de emails de cumpleaños
# ============================================================================


def birthday_form(request):
    """
    Vista para gestionar y enviar manualmente emails de cumpleaños.
    GET: Muestra cumpleaños de hoy y del mes, con preview
    POST: Envía manualmente los emails de cumpleaños de hoy
    """
    from .models import Student
    from .email import email_service

    today = date.today()
    birthday_students = Student.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day,
        active=True
    ).select_related('group')

    month_birthdays = Student.objects.filter(
        birth_date__month=today.month,
        active=True
    ).select_related('group').order_by('birth_date__day')

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _name = birthday_students.first().first_name if birthday_students.exists() else 'Alumno Ejemplo'
            _ctx = {'name': _name}
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/happy_birthday.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='happy_birthday',
                recipients=_recipients,
                subject=f'[TEST] 🎉 ¡Feliz Cumpleaños {_name}!',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        if not birthday_students.exists():
            messages.info(request, "ℹ️ No hay cumpleaños hoy")
            return redirect("birthday_form")

        success_count = 0
        error_count = 0
        for student in birthday_students:
            parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
            if not parent:
                continue
            try:
                result = email_service.send_email(
                    template_name='happy_birthday',
                    recipients=parent.email,
                    subject=f'🎉 ¡Feliz Cumpleaños {student.first_name}!',
                    context={'name': student.first_name}
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            messages.success(request, f"✅ Email de cumpleaños enviado a {success_count} estudiante(s)")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
        return redirect("birthday_form")

    email_html = render_to_string('emails/happy_birthday.html', {
        'name': 'Alumno',
    })
    return render(request, "apps/birthday_form.html", {
        "today": today.strftime('%d/%m/%Y'),
        "birthday_students": birthday_students,
        "month_birthdays": month_birthdays,
        "email_html": email_html,
    })


# ============================================================================
# RECIBOS - Generación y envío trimestral/mensual
# ============================================================================


def receipts_form(request):
    """
    Vista para enviar recibos trimestrales (niños) o mensuales (adultos).
    GET: Muestra formulario con opciones de trimestre/mes
    POST: Envía recibos a los padres correspondientes
    """
    from .models import Parent, Student
    from .email import send_quarterly_receipt_email

    today = date.today()
    current_month = MESES_ES[today.month - 1]
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    # Calcular trimestre actual
    quarter_idx = (today.month - 1) // 3
    quarter_start = quarter_idx * 3
    quarter_months = [MESES_ES[quarter_start], MESES_ES[quarter_start + 1], MESES_ES[quarter_start + 2]]

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _rtype = request.POST.get('receipt_type', 'quarterly_child')
            if _rtype == 'quarterly_child':
                _m1 = request.POST.get('month_1', quarter_months[0])
                _m2 = request.POST.get('month_2', quarter_months[1])
                _m3 = request.POST.get('month_3', quarter_months[2])
                _template = 'recibo_trimestre_niño'
                _ctx = {'student_name': 'Alumno Ejemplo', 'month_1': _m1, 'month_2': _m2, 'month_3': _m3}
                _subject = f'[TEST] 🧾 Recibo Trimestral - {_m1.title()}/{_m2.title()}/{_m3.title()}'
            else:
                _adm = request.POST.get('adult_month', current_month)
                _template = 'recibo_adulto'
                _ctx = {'month': _adm}
                _subject = f'[TEST] 🧾 Recibo Mensual - {_adm.title()}'
            if action == 'preview':
                return JsonResponse({'html': render_to_string(f'emails/{_template}.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name=_template,
                recipients=_recipients,
                subject=_subject,
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        receipt_type = request.POST.get("receipt_type", "quarterly_child")

        if receipt_type == "quarterly_child":
            month_1 = request.POST.get("month_1", quarter_months[0])
            month_2 = request.POST.get("month_2", quarter_months[1])
            month_3 = request.POST.get("month_3", quarter_months[2])

            parents = Parent.objects.filter(
                children__active=True
            ).distinct().prefetch_related('children')

            success_count = 0
            error_count = 0
            for parent in parents:
                if not parent.email:
                    continue
                for student in parent.children.filter(active=True):
                    try:
                        result = send_quarterly_receipt_email(
                            parent_email=parent.email,
                            student_name=student.full_name,
                            month_1=month_1,
                            month_2=month_2,
                            month_3=month_3,
                        )
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1
        else:
            adult_month = request.POST.get("adult_month", current_month)
            # Send adult receipts using the recibo_adulto template
            parents = Parent.objects.filter(
                children__active=True
            ).distinct()

            success_count = 0
            error_count = 0
            for parent in parents:
                if not parent.email:
                    continue
                try:
                    result = email_service.send_email(
                        template_name='recibo_adulto',
                        recipients=parent.email,
                        subject=f'🧾 Recibo Mensual - {adult_month.title()}',
                        context={'month': adult_month},
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

        if success_count > 0:
            messages.success(request, f"✅ Recibos enviados: {success_count}")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} recibo(s) no pudieron enviarse")
        return redirect("apps")

    email_html = render_to_string('emails/recibo_trimestre_niño.html', {
        'student_name': 'Alumno Ejemplo',
        'month_1': quarter_months[0],
        'month_2': quarter_months[1],
        'month_3': quarter_months[2],
    })
    return render(request, "apps/receipts_form.html", {
        "months": MESES_ES,
        "current_month": current_month,
        "quarter_months": quarter_months,
        "parent_count": parent_count,
        "email_html": email_html,
    })


# ============================================================================
# MATRÍCULAS - Confirmación de matrícula
# ============================================================================


def enrollment_form(request):
    """
    Vista para enviar confirmación de matrícula manualmente.
    GET: Muestra formulario con selector de estudiante
    POST: Envía confirmación al padre del estudiante seleccionado
    """
    from .models import Student
    from .email import send_enrollment_confirmation_email

    today = date.today()
    current_month = MESES_ES[today.month - 1]
    students = Student.objects.filter(active=True).select_related('group').order_by('last_name', 'first_name')

    # Academic year: if month >= September, current/next year, else previous/current
    if today.month >= 9:
        default_academic_year = f"{today.year}-{today.year + 1}"
    else:
        default_academic_year = f"{today.year - 1}-{today.year}"

    if request.method == "POST":
        action = request.POST.get('action', '')
        email_type = request.POST.get('email_type', 'enrollment')

        if action in ('preview', 'test_send'):
            _student_id = request.POST.get('student_id')
            if email_type == 'welcome':
                _ctx = {
                    'parent_name': 'Nombre del padre',
                    'student_name': 'Nombre del alumno',
                    'group_name': 'Grupo A',
                    'enrollment_type': 'Mensual',
                    'schedule_type': 'Jornada completa',
                    'start_date': '01/09/2025',
                }
                if _student_id:
                    try:
                        _s = Student.objects.select_related('group').get(id=_student_id)
                        _p = _s.parents.exclude(email='').exclude(email__isnull=True).first()
                        _ctx['student_name'] = _s.full_name
                        if _p:
                            _ctx['parent_name'] = _p.full_name
                        if _s.group:
                            _ctx['group_name'] = _s.group.group_name
                    except Exception:
                        pass
                if action == 'preview':
                    return JsonResponse({'html': render_to_string('emails/welcome_student.html', _ctx)})
                _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
                _recipients = [r for r in [_t1, _t2] if r]
                if not _recipients:
                    return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
                _ok = email_service.send_email(
                    template_name='welcome_student',
                    recipients=_recipients,
                    subject=f'[TEST] 🎉 Bienvenida a Five a Day - {_ctx["student_name"]}',
                    context=_ctx,
                )
                if _ok:
                    return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
                return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})
            else:
                _etype = request.POST.get('enrollment_type', 'child')
                _gender = request.POST.get('gender', 'm')
                _ay = request.POST.get('academic_year', default_academic_year)
                _month = request.POST.get('month', current_month)
                _student_name = 'Alumno Ejemplo'
                if _student_id:
                    try:
                        _s = Student.objects.get(id=_student_id)
                        _student_name = _s.full_name
                    except Exception:
                        pass
                _template = 'matricula_niño' if _etype == 'child' else 'matricula_adulto'
                _ctx = {'student': _student_name, 'genero': _gender, 'academic_year': _ay, 'month': _month}
                if action == 'preview':
                    return JsonResponse({'html': render_to_string(f'emails/{_template}.html', _ctx)})
                _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
                _recipients = [r for r in [_t1, _t2] if r]
                if not _recipients:
                    return JsonResponse({'ok': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
                _ok = email_service.send_email(
                    template_name=_template,
                    recipients=_recipients,
                    subject=f'[TEST] 🎉 Confirmación de Matrícula - {_student_name}',
                    context=_ctx,
                )
                if _ok:
                    return JsonResponse({'ok': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
                return JsonResponse({'ok': False, 'message': '❌ Error al enviar el email de prueba'})

        student_id = request.POST.get("student_id")
        if not student_id:
            messages.error(request, "❌ Selecciona un estudiante")
        elif email_type == 'welcome':
            from .email import send_welcome_email
            try:
                student = Student.objects.select_related('group').prefetch_related('parents').get(id=student_id)
                parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
                if not parent:
                    messages.error(request, f"❌ {student.full_name} no tiene padre con email registrado")
                else:
                    result = send_welcome_email(
                        parent_email=parent.email,
                        parent_name=parent.full_name,
                        student_name=student.full_name,
                        group_name=student.group.group_name if student.group else None,
                    )
                    if result:
                        messages.success(request, f"✅ Email de bienvenida enviado a {parent.email}")
                    else:
                        messages.error(request, "❌ Error al enviar el email")
            except Student.DoesNotExist:
                messages.error(request, "❌ Estudiante no encontrado")
        else:
            enrollment_type = request.POST.get("enrollment_type", "child")
            gender = request.POST.get("gender", "m")
            academic_year = request.POST.get("academic_year", default_academic_year)
            month = request.POST.get("month", current_month)
            try:
                student = Student.objects.prefetch_related('parents').get(id=student_id)
                parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
                if not parent:
                    messages.error(request, f"❌ {student.full_name} no tiene padre con email registrado")
                else:
                    template = 'matricula_niño' if enrollment_type == 'child' else 'matricula_adulto'
                    result = email_service.send_email(
                        template_name=template,
                        recipients=parent.email,
                        subject=f'🎉 Confirmación de Matrícula - {student.full_name}',
                        context={
                            'student': student.full_name,
                            'genero': gender,
                            'academic_year': academic_year,
                            'month': month,
                        },
                    )
                    if result:
                        messages.success(request, f"✅ Confirmación de matrícula enviada a {parent.email}")
                    else:
                        messages.error(request, "❌ Error al enviar el email")
            except Student.DoesNotExist:
                messages.error(request, "❌ Estudiante no encontrado")
        return redirect("enrollment_form")

    email_html = render_to_string('emails/welcome_student.html', {
        'parent_name': 'Nombre del padre',
        'student_name': 'Nombre del alumno',
        'group_name': 'Grupo A',
        'enrollment_type': 'Mensual',
        'schedule_type': 'Jornada completa',
        'start_date': '01/09/2025',
    })
    return render(request, "apps/enrollment_form.html", {
        "students": students,
        "months": MESES_ES,
        "current_month": current_month,
        "default_academic_year": default_academic_year,
        "email_html": email_html,
    })


# ============================================================================
# SISTEMA DE SOPORTE - Tickets de ayuda
# ============================================================================


@require_http_methods(["POST"])
def submit_support_ticket(request):
    """
    Endpoint API para recibir tickets de soporte.
    Envía un email al SUPPORT_EMAIL con los detalles del ticket.
    """
    from django.core.mail import send_mail
    from datetime import datetime

    try:
        data = json.loads(request.body)

        category = data.get("category", "exception")
        category_display = data.get("category_display", "otro")
        message = data.get("message", "").strip()
        current_url = data.get("current_url", "/")

        # Validar mensaje
        if not message or len(message) < 10:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El mensaje debe tener al menos 10 caracteres",
                },
                status=400,
            )

        # Obtener información del usuario
        username = request.session.get("username", "Anónimo")

        # Versión del software
        version = settings.APP_VERSION

        # Fecha y hora actual
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Obtener SUPPORT_EMAIL desde settings
        support_email = getattr(settings, "SUPPORT_EMAIL", None)

        if not support_email:
            return JsonResponse(
                {"success": False, "message": "Email de soporte no configurado"},
                status=500,
            )

        # Construir el email
        subject = f"[{category.upper()}] Ticket de Soporte - Five a Day"

        email_body = f"""
═══════════════════════════════════════════════════════════
                    TICKET DE SOPORTE
═══════════════════════════════════════════════════════════

📋 INFORMACIÓN DEL TICKET
───────────────────────────────────────────────────────────
Tipo:           {category} ({category_display})
Versión:        {version}
Fecha/Hora:     {now}
Usuario:        {username}
Vista actual:   {current_url}

💬 MENSAJE
───────────────────────────────────────────────────────────
{message}

═══════════════════════════════════════════════════════════
                    Five a Day - eVolution
═══════════════════════════════════════════════════════════
"""

        # Enviar email
        send_mail(
            subject=subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[support_email],
            fail_silently=False,
        )

        return JsonResponse(
            {"success": True, "message": "Ticket enviado correctamente"}
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Datos inválidos"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error al enviar ticket: {str(e)}"},
            status=500,
        )


# ============================================================================
# SCHEDULE - Horario semanal
# ============================================================================

def schedule_view(request):
    """Vista del horario semanal estilo Google Calendar."""
    groups = Group.objects.filter(active=True).select_related('teacher').prefetch_related(
        models.Prefetch('students', queryset=Student.objects.filter(active=True).order_by('first_name'))
    ).order_by('group_name')

    groups_list = list(groups)
    groups_data = []
    for g in groups_list:
        groups_data.append({
            "id": g.id,
            "name": g.group_name,
            "color": g.color,
            "teacher": g.teacher.first_name,
            "students": [s.first_name for s in g.students.all()],
        })

    # Only load explicitly saved slots — no auto-fill
    saved = ScheduleSlot.objects.select_related('group').all()
    ROW_STARTS = ['16:10', '17:40', '19:10']
    ROW_ENDS   = ['17:30', '19:00', '20:30']
    FRI_START  = '16:00'
    FRI_END    = '17:20'
    slots_data = []
    for s in saved:
        if s.day == 4:
            start, end = FRI_START, FRI_END
        else:
            start, end = ROW_STARTS[s.row], ROW_ENDS[s.row]
        slots_data.append({"row": s.row, "day": s.day, "col": s.col, "group_id": s.group_id, "start": start, "end": end})

    all_students = Student.objects.filter(active=True).order_by('first_name', 'last_name')
    students_data = [{"first_name": s.first_name, "last_name": s.last_name} for s in all_students]

    return render(request, "schedule.html", {
        "groups_json": json.dumps(groups_data),
        "slots_json": json.dumps(slots_data),
        "students_json": json.dumps(students_data),
    })


@require_http_methods(["POST"])
def save_schedule_slot(request):
    """Save a single schedule slot assignment to the database."""
    try:
        data = json.loads(request.body)
        row = int(data['row'])
        day = int(data['day'])
        col = int(data['col'])
        group_id = data.get('group_id')

        if group_id:
            group = get_object_or_404(Group, id=int(group_id))
            ScheduleSlot.objects.update_or_create(
                row=row, day=day, col=col,
                defaults={'group': group}
            )
        else:
            ScheduleSlot.objects.filter(row=row, day=day, col=col).delete()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)


# ============================================================================
# FUN FRIDAY - Lista de estudiantes
# ============================================================================

def fun_friday_view(request):
    """Vista de Fun Friday con lista de estudiantes."""
    students = Student.objects.filter(active=True, is_adult=False).select_related('group').order_by('group__group_name', 'first_name')
    this_friday = get_next_friday()
    last_friday = get_last_friday()
    this_week_ids = get_ff_student_ids(this_friday)
    last_week_ids = get_ff_student_ids(last_friday)
    this_week_students = Student.objects.filter(id__in=this_week_ids).order_by('first_name', 'last_name')
    last_week_students = Student.objects.filter(id__in=last_week_ids).order_by('first_name', 'last_name')
    return render(request, "fun_friday.html", {
        "students": students,
        "this_week_ids": this_week_ids,
        "last_week_ids": last_week_ids,
        "this_friday": this_friday,
        "last_friday": last_friday,
        "this_week_students": this_week_students,
        "last_week_students": last_week_students,
    })
