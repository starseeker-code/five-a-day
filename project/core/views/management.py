import json
from decimal import Decimal

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods

from billing import constants
from billing.models import Enrollment, SiteConfiguration, current_academic_year
from core.models import HistoryLog
from students.models import Group, Student, Teacher


def gestion_view(request):
    """
    Vista principal de gestión con configuración de precios, profesores y grupos.
    """
    config = SiteConfiguration.get_config()
    teachers = Teacher.objects.filter(active=True).order_by("first_name", "last_name")
    groups = Group.objects.filter(active=True).select_related("teacher").order_by("group_name")

    context = {
        "config": config,
        "teachers": teachers,
        "groups": groups,
    }
    return render(request, "management.html", context)


@require_http_methods(["POST"])
def update_site_config(request):
    """API para actualizar la configuración de precios del sitio."""
    try:
        data = json.loads(request.body)
        config = SiteConfiguration.get_config()

        if "children_enrollment_fee" in data:
            config.children_enrollment_fee = Decimal(str(data["children_enrollment_fee"]))
        if "adult_enrollment_fee" in data:
            config.adult_enrollment_fee = Decimal(str(data["adult_enrollment_fee"]))

        if "full_time_monthly_fee" in data:
            config.full_time_monthly_fee = Decimal(str(data["full_time_monthly_fee"]))
        if "part_time_monthly_fee" in data:
            config.part_time_monthly_fee = Decimal(str(data["part_time_monthly_fee"]))
        if "adult_group_monthly_fee" in data:
            config.adult_group_monthly_fee = Decimal(str(data["adult_group_monthly_fee"]))

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

        HistoryLog.log("config_updated", "Precios o descuentos actualizados", icon="tune")

        return JsonResponse({"success": True, "message": "Configuración actualizada correctamente"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=400)


@require_http_methods(["POST"])
def create_teacher(request):
    """API para crear un nuevo profesor."""
    try:
        data = json.loads(request.body)

        required_fields = ["first_name", "last_name", "email"]
        for field in required_fields:
            if not data.get(field):
                return JsonResponse(
                    {"success": False, "message": f"El campo {field} es requerido"},
                    status=400,
                )

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

        HistoryLog.log("teacher_created", f"Profesor creado: {teacher.full_name}", icon="person_add")

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
    """API para crear un nuevo grupo."""
    try:
        data = json.loads(request.body)

        if not data.get("group_name"):
            return JsonResponse(
                {"success": False, "message": "El nombre del grupo es requerido"},
                status=400,
            )

        if not data.get("teacher_id"):
            return JsonResponse({"success": False, "message": "El profesor es requerido"}, status=400)

        if Group.objects.filter(group_name=data["group_name"]).exists():
            return JsonResponse(
                {"success": False, "message": "Ya existe un grupo con ese nombre"},
                status=400,
            )

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

        HistoryLog.log(
            "group_created", f"Grupo creado: {group.group_name} (Prof. {teacher.full_name})", icon="group_add"
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
    """API para obtener lista de profesores activos (para select de grupos)."""
    teachers = Teacher.objects.filter(active=True).order_by("first_name", "last_name")
    data = [{"id": t.id, "full_name": t.full_name, "email": t.email} for t in teachers]
    return JsonResponse({"teachers": data})


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

        enrollment = student.enrollments.filter(status="active").first()
        if not enrollment:
            return JsonResponse(
                {"success": False, "error": "No tiene matrícula activa"},
                status=404,
            )

        enrollment.payment_modality = modality
        enrollment.save()

        return JsonResponse(
            {
                "success": True,
                "message": f"Modalidad cambiada a {enrollment.get_payment_modality_display()}.",
                "payment_modality": modality,
                "payment_modality_display": enrollment.get_payment_modality_display(),
            }
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": str(e)},
            status=500,
        )


@require_http_methods(["GET"])
def language_cheque_students(request):
    """
    API endpoint to fetch students with active language cheque (cheque idioma).
    """
    academic_year = current_academic_year()
    enrollments = (
        Enrollment.objects.filter(
            status="active",
            academic_year=academic_year,
            has_language_cheque=True,
        )
        .select_related("student", "student__group")
        .prefetch_related("student__parents")
    )

    students_data = []
    for enrollment in enrollments:
        s = enrollment.student
        parent = s.parents.first()
        students_data.append(
            {
                "id": s.id,
                "full_name": s.full_name,
                "birth_date": s.birth_date.strftime("%Y-%m-%d"),
                "group": s.group.group_name if s.group else "",
                "parent_name": parent.full_name if parent else "",
                "parent_dni": parent.dni if parent else "",
                "schedule_type": enrollment.get_schedule_type_display(),
            }
        )

    return JsonResponse(
        {
            "success": True,
            "academic_year": academic_year,
            "count": len(students_data),
            "students": students_data,
        }
    )
