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
from django.urls import reverse_lazy
from decimal import Decimal, InvalidOperation
import json
from datetime import date, datetime
from core.transactions import all_students, all_payments
from core.forms import StudentForm, ParentForm, EnrollmentForm, ParentFormSet
from core.email import email_service
from django.template.loader import render_to_string
from django.conf import settings
import os

# Registry of scheduled apps/emails.
# frequency options: 'every_friday' | 'monthly_day_1' | 'manual' | 'yearly_april'
#                    'monthly_last_day' | 'on_student_creation' | 'daily'
#                    'quarterly' | 'on_enrollment'
SCHEDULED_APPS = [
    {"name": "Fun Friday", "url_name": "fun_friday_form", "frequency": "every_friday", "active": True},
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
    # Si ya está autenticado, redirigir al home
    if request.session.get("is_authenticated"):
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Validar contra credenciales en .env
        valid_username = os.getenv("LOGIN_USERNAME", "fiveaday")
        valid_password = os.getenv("LOGIN_PASSWORD", "Fiveaday123!")

        if username == valid_username and password == valid_password:
            # Autenticación exitosa
            request.session["is_authenticated"] = True
            request.session["username"] = username
            messages.success(request, f"¡Bienvenido {username}!")
            return redirect("home")
        else:
            # Credenciales incorrectas
            messages.error(request, "❌ Usuario o contraseña incorrectos")

    return render(request, "login.html")


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

    # Obtener nombres únicos de estudiantes con pagos pendientes (máximo 5)
    pending_students = []
    seen_students = set()
    for payment in pending_payments:
        if payment.student_id not in seen_students:
            seen_students.add(payment.student_id)
            pending_students.append(payment.student.first_name)

    pending_students_display = pending_students[:5]
    has_more_pending = len(pending_students) > 5

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

    context = {
        "pending_payments_count": pending_count,
        "pending_students": pending_students_display,
        "has_more_pending": has_more_pending,
        "total_pending_students": len(pending_students),
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
    from core.transactions import all_payments_unrestricted

    return render(
        request,
        "all_info.html",
        {"students": list(all_students), "payments": list(all_payments_unrestricted)},
    )


def apps_view(request):
    """Vista para la página de aplicaciones/herramientas"""
    return render(request, "apps.html")


def email_test(request):
    """
    Vista para probar el envío de emails.
    Uso: /email/?email=destinatario@example.com
    Envía un email de cumpleaños inmediatamente y uno de bienvenida a los 5 segundos.
    """
    recipient = request.GET.get("email")

    if not recipient:
        return JsonResponse(
            {
                "error": 'Parámetro "email" requerido',
                "uso": "/email/?email=tu@email.com",
                "ejemplo": "/email/?email=test@gmail.com",
            },
            status=400,
        )

    try:
        from datetime import datetime
        import threading
        import time

        # Enviar email de cumpleaños inmediatamente
        success_birthday = email_service.send_email(
            template_name="happy_birthday",
            recipients=recipient,
            subject="🎉 ¡Feliz Cumpleaños! - Five a Day (Prueba)",
            context={"name": "Estudiante de Prueba", "year": datetime.now().year},
        )

        # Función para enviar email de bienvenida después de 5 segundos
        def send_welcome_delayed():
            time.sleep(5)
            email_service.send_email(
                template_name="welcome_student",
                recipients=recipient,
                subject="🎓 ¡Bienvenido a Five a Day! (Prueba)",
                context={
                    "student_name": "Estudiante de Prueba",
                    "parent_name": "Padre/Madre de Prueba",
                    "group_name": "Grupo de Ejemplo",
                    "teacher_name": "Profesor de Prueba",
                    "schedule_type": "Completo",
                    "enrollment_fee": "50.00",
                    "monthly_fee": "100.00",
                    "year": datetime.now().year,
                },
            )

        # Lanzar el email de bienvenida en un hilo separado
        threading.Thread(target=send_welcome_delayed, daemon=True).start()

        if success_birthday:
            return JsonResponse(
                {
                    "success": True,
                    "message": f"Email de cumpleaños enviado a {recipient}. Email de bienvenida se enviará en 5 segundos.",
                    "templates": ["happy_birthday", "welcome_student (en 5s)"],
                }
            )
        else:
            return JsonResponse(
                {
                    "success": False,
                    "error": "Error al enviar email. Verifica la configuración SMTP.",
                },
                status=500,
            )

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


# ---> Estudiantes | Pagos || DASHBOARDS (Home + Info) | Aplicaciones | Facturacion | UI! || Gastos | Renta | UI!! || Configuracion | Contacto y ayuda
# TESTING CODE ("testing/")


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
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = self.object
                enrollment.save()
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

        # Obtener el parent_id de los parámetros GET si existe
        parent_id = self.request.GET.get("parent_id")

        if parent_id:
            try:
                parent = Parent.objects.get(id=parent_id)
                context["parent"] = parent
                context["parent_id"] = parent_id
            except Parent.DoesNotExist:
                messages.error(self.request, "El padre especificado no existe")

        # Agregar el formulario de matrícula
        if "enrollment_form" not in context:
            context["enrollment_form"] = EnrollmentForm(self.request.POST or None)

        # Agregar grupos disponibles
        context["groups"] = Group.objects.filter(active=True)

        # Agregar precios de configuración para JavaScript
        config = SiteConfiguration.get_config()
        context["price_config"] = {
            "full_time": str(config.full_time_monthly_fee),
            "part_time": str(config.part_time_monthly_fee),
            "adult_group": str(config.adult_group_monthly_fee),
        }

        return context

    def form_valid(self, form):
        from core.tasks import send_welcome_email_task

        enrollment_form = EnrollmentForm(self.request.POST)

        if not enrollment_form.is_valid():
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                # Crear el estudiante
                student = form.save()

                # Obtener el parent_id del POST o GET
                parent_id = self.request.POST.get("parent_id") or self.request.GET.get(
                    "parent_id"
                )

                if not parent_id:
                    messages.error(
                        self.request, "Debe especificar un padre para el estudiante"
                    )
                    student.delete()
                    return self.form_invalid(form)

                # Vincular al padre
                try:
                    parent = Parent.objects.get(id=parent_id)
                    student.parents.add(parent)
                except Parent.DoesNotExist:
                    messages.error(self.request, "El padre especificado no existe")
                    student.delete()
                    return self.form_invalid(form)

                # Crear la matrícula
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = student
                enrollment.save()

                # Encolar email de bienvenida de forma asíncrona (Celery)
                try:
                    send_welcome_email_task.delay(
                        parent_id=parent.id,
                        student_id=student.id,
                        enrollment_id=enrollment.id,
                    )
                except Exception as celery_error:
                    # Si Celery no está disponible, no fallar
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"No se pudo encolar email de bienvenida: {celery_error}"
                    )

                messages.success(
                    self.request,
                    f"¡Estudiante {student.full_name} creado exitosamente!",
                )

                # Verificar si el usuario quiere crear otro hermano
                if "create_sibling" in self.request.POST:
                    # Redirigir a crear otro estudiante con el mismo padre
                    return HttpResponseRedirect(
                        reverse_lazy("student_create") + f"?parent_id={parent_id}"
                    )
                else:
                    # Redirigir a la lista de estudiantes
                    return HttpResponseRedirect(reverse_lazy("students_list"))

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
        queryset = (
            Student.objects.filter(active=True)
            .select_related("group")
            .prefetch_related("parents")
        )

        # Búsqueda opcional
        search_query = self.request.GET.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
            )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["groups"] = Group.objects.filter(active=True)
        context["parents"] = Parent.objects.all()
        context["fun_friday_ids"] = set()
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

        if "enrollment_form" not in context:
            context["enrollment_form"] = EnrollmentForm(
                self.request.POST or None, instance=enrollment
            )

        context["parents"] = self.object.parents.all()
        context["groups"] = Group.objects.filter(active=True)

        return context

    def form_valid(self, form):
        try:
            enrollment = self.object.enrollments.filter(status="active").latest(
                "created_at"
            )
        except Enrollment.DoesNotExist:
            enrollment = None

        enrollment_form = EnrollmentForm(self.request.POST, instance=enrollment)

        if not enrollment_form.is_valid():
            return self.form_invalid(form)

        try:
            with transaction.atomic():
                student = form.save()

                enrollment = enrollment_form.save(commit=False)
                enrollment.student = student
                enrollment.save()

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
        try:
            enrollment = self.object.enrollments.filter(status="active").latest(
                "created_at"
            )
        except Enrollment.DoesNotExist:
            enrollment = None
        context["enrollment_form"] = EnrollmentForm(
            self.request.POST, instance=enrollment
        )
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
        return context


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
        "student", "parent", "enrollment"
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
    expected_payments_total = Payment.objects.filter(
        due_date__month=current_month,
        due_date__year=current_year,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Completed: payments completed this month
    completed_payments_total = Payment.objects.filter(
        payment_status="completed",
        payment_date__month=current_month,
        payment_date__year=current_year,
    ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

    # Pagination - 10 payments per page, max 100 total
    paginator = Paginator(payments_queryset[:100], 10)
    page_number = request.GET.get("page", 1)
    payments = paginator.get_page(page_number)

    context = {
        "payments": payments,
        "search_query": search_query,
        "expected_payments_total": expected_payments_total,
        "completed_payments_total": completed_payments_total,
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

    return redirect("payments_list")


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
def create_payment(request):
    """
    AJAX endpoint to create new payment
    """
    try:
        # Parse form data (works with both FormData and JSON)
        if request.content_type == "application/json":
            data = json.loads(request.body)
        else:
            data = request.POST

        # Get required data
        student_id = data.get("student_id")
        parent_id = data.get("parent_id")

        # Validate required fields
        if not student_id or not parent_id:
            if request.content_type == "application/json":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "Student ID and Parent ID are required",
                    },
                    status=400,
                )
            messages.error(request, "Debe seleccionar estudiante y padre/tutor.")
            return redirect("payments_list")

        # Validate student and parent exist
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)

        # Validate relationship
        if not student.parents.filter(id=parent_id).exists():
            if request.content_type == "application/json":
                return JsonResponse(
                    {
                        "success": False,
                        "error": "El padre/tutor seleccionado no está asociado con este estudiante.",
                    },
                    status=400,
                )
            messages.error(
                request,
                "El padre/tutor seleccionado no está asociado con este estudiante.",
            )
            return redirect("payments_list")

        # Get enrollment if exists
        enrollment = student.enrollments.filter(status="active").first()

        due_date = parse_date_value(data.get("due_date"))
        payment_date = parse_date_value(data.get("payment_date"))

        # Create payment
        payment = Payment.objects.create(
            student=student,
            parent=parent,
            enrollment=enrollment,
            payment_type=data.get("payment_type"),
            payment_method=data.get("payment_method"),
            amount=Decimal(data.get("amount")),
            currency=data.get("currency", "EUR"),
            payment_status=data.get("payment_status", "pending"),
            due_date=due_date,
            payment_date=payment_date,
            concept=data.get("concept"),
            reference_number=data.get("reference_number", ""),
            observations=data.get("observations", ""),
        )

        if request.content_type != "application/json":
            messages.success(
                request, f"Pago creado exitosamente para {student.full_name}."
            )
            return redirect("payments_list")

        return JsonResponse(
            {
                "success": True,
                "message": f"Pago creado exitosamente para {student.full_name}.",
                "payment": {
                    "id": payment.id,
                    "student_name": payment.student.full_name,
                    "parent_name": payment.parent.full_name,
                    "amount": str(payment.amount),
                    "currency": payment.currency,
                    "payment_status": payment.get_payment_status_display(),
                    "due_date": (
                        payment.due_date.strftime("%Y-%m-%d")
                        if payment.due_date
                        else ""
                    ),
                    "concept": payment.concept,
                },
            }
        )

    except InvalidOperation:
        if request.content_type == "application/json":
            return JsonResponse(
                {
                    "success": False,
                    "error": "Monto inválido. Por favor ingrese un número válido.",
                },
                status=400,
            )
        messages.error(request, "Monto inválido. Por favor ingrese un número válido.")
        return redirect("payments_list")
    except ValidationError as e:
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
                {"success": False, "error": f"Error al crear el pago: {str(e)}"},
                status=500,
            )
        messages.error(request, f"Error al crear el pago: {str(e)}")
        return redirect("payments_list")


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
                    "parent_id": payment.parent.id,
                    "parent_name": payment.parent.full_name,
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
    return render(request, "gestion.html", context)


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
            group_name=data["group_name"], teacher=teacher, active=True
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

    # Contar padres con estudiantes activos
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

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
    """
    Vista para reenviar emails de bienvenida manualmente.
    GET: Muestra selector de estudiante y preview
    POST: Envía email de bienvenida al padre del estudiante seleccionado
    """
    from .models import Student, Parent
    from .email import send_welcome_email

    students = Student.objects.filter(active=True).select_related('group').order_by('last_name', 'first_name')

    if request.method == "POST":
        student_id = request.POST.get("student_id")
        if not student_id:
            messages.error(request, "❌ Selecciona un estudiante")
        else:
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
        return redirect("welcome_form")

    email_html = render_to_string('emails/welcome_student.html', {
        'parent_name': 'Nombre del padre',
        'student_name': 'Nombre del alumno',
        'group_name': 'Grupo A',
        'enrollment_type': 'Mensual',
        'schedule_type': 'Jornada completa',
        'start_date': '01/09/2025',
    })
    return render(request, "apps/welcome_form.html", {
        "students": students,
        "email_html": email_html,
    })


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
        student_id = request.POST.get("student_id")
        enrollment_type = request.POST.get("enrollment_type", "child")
        gender = request.POST.get("gender", "m")
        academic_year = request.POST.get("academic_year", default_academic_year)
        month = request.POST.get("month", current_month)

        if not student_id:
            messages.error(request, "❌ Selecciona un estudiante")
        else:
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

    email_html = render_to_string('emails/matricula_niño.html', {
        'student': 'Alumno Ejemplo',
        'genero': 'm',
        'academic_year': default_academic_year,
        'month': 'septiembre',
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

    groups_data = []
    for g in groups:
        groups_data.append({
            "id": g.id,
            "name": g.group_name,
            "teacher": g.teacher.first_name,
            "students": [s.first_name for s in g.students.all()],
        })

    all_students = Student.objects.filter(active=True).order_by('first_name', 'last_name')
    students_data = [{"first_name": s.first_name, "last_name": s.last_name} for s in all_students]

    return render(request, "schedule.html", {
        "groups_json": json.dumps(groups_data),
        "students_json": json.dumps(students_data),
    })


# ============================================================================
# FUN FRIDAY - Lista de estudiantes
# ============================================================================

def fun_friday_view(request):
    """Vista de Fun Friday con lista de estudiantes."""
    students = Student.objects.filter(active=True).select_related('group__teacher').order_by('group__group_name', 'first_name')
    return render(request, "fun_friday.html", {"students": students})
