from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db.models import Q, Sum, Case, When, Value, DecimalField
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from decimal import Decimal, InvalidOperation
import json
import csv
import logging
from datetime import date, datetime

from billing.models import Payment, Enrollment
from students.models import Student, Parent
from core.models import HistoryLog
from billing import constants

logger = logging.getLogger(__name__)


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

    # Monthly payment totals — single aggregate query with Case/When
    today = date.today()
    current_month = today.month
    current_year = today.year

    _zero = Decimal("0.00")
    stats = Payment.objects.aggregate(
        expected_total=Sum(Case(
            When(due_date__month=current_month, due_date__year=current_year, then='amount'),
            default=Value(0), output_field=DecimalField(),
        )),
        expected_count=Sum(Case(
            When(due_date__month=current_month, due_date__year=current_year, then=Value(1)),
            default=Value(0),
        )),
        completed_total=Sum(Case(
            When(payment_status="completed", payment_date__month=current_month, payment_date__year=current_year, then='amount'),
            default=Value(0), output_field=DecimalField(),
        )),
        completed_count=Sum(Case(
            When(payment_status="completed", payment_date__month=current_month, payment_date__year=current_year, then=Value(1)),
            default=Value(0),
        )),
        pending_total=Sum(Case(
            When(payment_status="pending", then='amount'),
            default=Value(0), output_field=DecimalField(),
        )),
        pending_count=Sum(Case(
            When(payment_status="pending", then=Value(1)),
            default=Value(0),
        )),
        overdue_total=Sum(Case(
            When(payment_status="pending", due_date__lt=today, then='amount'),
            default=Value(0), output_field=DecimalField(),
        )),
        overdue_count=Sum(Case(
            When(payment_status="pending", due_date__lt=today, then=Value(1)),
            default=Value(0),
        )),
    )

    all_payments_list = list(payments_queryset[:1000])

    context = {
        "payments_list": all_payments_list,
        "total_count": payments_queryset.count(),
        "search_query": search_query,
        "expected_payments_total": stats["expected_total"] or _zero,
        "expected_payments_count": stats["expected_count"] or 0,
        "completed_payments_total": stats["completed_total"] or _zero,
        "completed_payments_count": stats["completed_count"] or 0,
        "pending_payments_total": stats["pending_total"] or _zero,
        "pending_payments_count": stats["pending_count"] or 0,
        "overdue_payments_total": stats["overdue_total"] or _zero,
        "overdue_payments_count": stats["overdue_count"] or 0,
        "payment_method_choices": constants.PAYMENT_METHOD_CHOICES,
    }

    return render(request, "payments/payments_list.html", context)


@require_http_methods(["GET", "POST"])
def create_payment(request):
    """
    Create new payment
    """
    from core.models import HistoryLog

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
            payment = Payment.objects.create(
                student=student,
                parent=parent,
                enrollment=enrollment,
                payment_type=request.POST.get("payment_type"),
                payment_method=request.POST.get("payment_method"),
                amount=Decimal(str(request.POST.get("amount", "0"))),
                currency=request.POST.get("currency", "EUR"),
                payment_status=request.POST.get("payment_status", "pending"),
                due_date=request.POST.get("due_date"),
                payment_date=request.POST.get("payment_date") or None,
                concept=request.POST.get("concept"),
                reference_number=request.POST.get("reference_number", ""),
                observations=request.POST.get("observations", ""),
            )
            HistoryLog.log(
                'payment_created',
                f'Pago creado: {student.full_name} — €{payment.amount} ({payment.get_payment_type_display()})',
                icon='add_card'
            )
            messages.success(
                request, f"Pago creado exitosamente para {student.full_name}."
            )
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


def payment_detail_view(request, payment_id):
    """
    Detailed view of a payment (read-only)
    """
    payment = get_object_or_404(Payment, id=payment_id)

    context = {
        "payment": payment,
    }

    return render(request, "payments/payment_detail.html", context)


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
        logger.exception("Error deleting payment %s", payment_id)

        return JsonResponse(
            {"success": False, "error": f"Error al eliminar el pago: {str(e)}"},
            status=500,
        )


# Soft delete!
@require_http_methods(["POST"])
def deactivate_payment(request, payment_id):
    """
    Soft delete - deactivate payment instead of deleting
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        payment.payment_status = 'cancelled'
        payment.save()

        return JsonResponse(
            {"success": True, "message": f"Pago desactivado exitosamente."}
        )

    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error al desactivar el pago: {str(e)}"},
            status=400,
        )


@require_http_methods(["POST"])
def quick_complete_payment(request, payment_id):
    """
    AJAX endpoint to quickly complete a payment by setting its payment method.
    Expects JSON body: {"payment_method": "cash"|"transfer"|"credit_card"}
    """
    from core.models import HistoryLog

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

        HistoryLog.log(
            'payment_completed',
            f'Pago completado: {payment.student.full_name} — {payment.get_payment_method_display()} (€{payment.amount})',
            icon='paid'
        )

        return JsonResponse({
            "success": True,
            "message": f"Pago de {payment.student.full_name} completado ({payment.get_payment_method_display()}).",
        })

    except Exception as e:
        return JsonResponse(
            {"success": False, "error": f"Error al completar el pago: {str(e)}"},
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


def payment_statistics(request):
    """
    Get payment statistics for dashboard
    """
    today = date.today()

    stats = {
        "total_payments": Payment.objects.count(),
        "completed_payments": Payment.objects.filter(
            payment_status="completed"
        ).count(),
        "pending_payments": Payment.objects.filter(
            payment_status="pending"
        ).count(),
        "overdue_payments": Payment.objects.filter(
            payment_status="pending", due_date__lt=today
        ).count(),
        "total_amount_pending": Payment.objects.filter(
            payment_status="pending"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
        "total_amount_completed": Payment.objects.filter(
            payment_status="completed"
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00"),
    }

    return JsonResponse(stats)


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


def export_payments(request):
    """
    Export payments to CSV
    """
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
        Payment.objects.all()
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
    from billing.exports import build_database_workbook

    wb = build_database_workbook()
    today = datetime.now().strftime("%Y%m%d")
    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = f'attachment; filename="five_a_day_{today}.xlsx"'
    wb.save(response)
    return response


def search_parents(request):
    """AJAX endpoint to search parents"""
    query = request.GET.get("q", "").strip()

    if len(query) < 2:
        return JsonResponse({"results": []})

    parents = Parent.objects.filter(
        Q(first_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
    )[:10]

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
    """AJAX endpoint to validate student-parent relationship"""
    try:
        data = json.loads(request.body)
        student_id = data.get("student_id")
        parent_id = data.get("parent_id")

        if not student_id or not parent_id:
            return JsonResponse(
                {"valid": False, "message": "Missing student or parent ID"}
            )

        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)

        is_valid = student.parents.filter(id=parent_id).exists()

        response_data = {
            "valid": is_valid,
            "message": "Valid relationship" if is_valid else "Invalid relationship",
        }

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
