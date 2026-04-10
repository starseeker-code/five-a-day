from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.views.generic import DetailView, ListView, UpdateView, CreateView
from django.http import HttpResponseRedirect, JsonResponse
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from datetime import date
import json

from students.models import Student, Parent, Group
from billing.models import Enrollment, Payment, SiteConfiguration, current_academic_year
from core.models import FunFridayAttendance, HistoryLog
from students.forms import StudentForm, ParentForm
from billing.forms import EnrollmentForm
from billing import constants


# ============================================================================
# PARENT AND STUDENT MANAGEMENT - Parent-First Flow
# ============================================================================


class StudentCreateView(CreateView):
    """
    Vista para crear un nuevo estudiante.
    Puede recibir un parent_id como parámetro GET para pre-vincular al padre.
    """

    model = Student
    form_class = StudentForm
    template_name = "student_create.html"

    def get_context_data(self, **kwargs):
        from billing.models import SiteConfiguration

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
        from comms.tasks import send_welcome_email_task
        from billing.models import SiteConfiguration
        from core.models import HistoryLog
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
                    student.gdpr_signed = True
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

                HistoryLog.log(
                    'student_enrolled',
                    f'Alumno matriculado: {student.full_name} — {enrollment.get_schedule_type_display()}',
                    icon='school'
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
        from billing.models import current_academic_year

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
        from billing.models import current_academic_year

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
# STUDENT HELPER FBVs
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
    from core.models import HistoryLog

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
                    student = Student.objects.select_related('group').get(id=student_id)
                    old_group = student.group

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

                    if old_group != group:
                        HistoryLog.log(
                            'group_updated',
                            f'Grupo cambiado: {student.full_name} — {old_group.group_name} → {group.group_name}',
                            icon='swap_horiz'
                        )

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
