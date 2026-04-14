from django.test import Client

from core.models import Enrollment, EnrollmentType, Group, Parent, Payment, Student, Teacher


def run():
    teacher, _ = Teacher.objects.get_or_create(
        email="smoke.teacher@fiveaday.test",
        defaults={
            "first_name": "Smoke",
            "last_name": "Teacher",
            "phone": "600000001",
            "active": True,
        },
    )

    group, _ = Group.objects.get_or_create(
        group_name="Smoke Group",
        defaults={"teacher": teacher, "active": True},
    )

    if group.teacher_id != teacher.id:
        group.teacher = teacher
        group.active = True
        group.save(update_fields=["teacher", "active"])

    parent, _ = Parent.objects.get_or_create(
        dni="SMOKE1234A",
        defaults={
            "first_name": "Padre",
            "last_name": "Prueba",
            "phone": "600000002",
            "email": "parent.smoke@fiveaday.test",
            "iban": "",
        },
    )

    enrollment_type = EnrollmentType.objects.filter(active=True).exclude(name="special").first()
    is_special = False
    if not enrollment_type:
        enrollment_type = EnrollmentType.objects.filter(active=True).first()
        is_special = bool(enrollment_type and enrollment_type.name == "special")
    if not enrollment_type:
        raise RuntimeError("No hay tipos de matrícula activos")

    client = Client(HTTP_HOST="localhost")
    session = client.session
    session["is_authenticated"] = True
    session.save()

    student_post_data = {
        "first_name": "Alumno",
        "last_name": "Smoke",
        "birth_date": "15/02/2015",
        "school": "Colegio Smoke",
        "allergies": "",
        "gdpr_signed": "on",
        "group": str(group.id),
        "parent_id": str(parent.id),
        "enrollment_type": str(enrollment_type.id),
        "academic_year": "2025-2026",
        "schedule_type": "full_time",
        "discount_percentage": "0",
        "enrollment_date": "27/02/2026",
        "status": "active",
        "notes": "Smoke test",
    }
    if is_special:
        student_post_data["manual_amount"] = "40.00"

    student_response = client.post("/students/create/", data=student_post_data, secure=True)

    student = Student.objects.filter(first_name="Alumno", last_name="Smoke").order_by("-id").first()
    if not student:
        print(f"student_response_status={student_response.status_code}")
        location = student_response.headers.get("Location")
        if location:
            print(f"student_location={location}")
        print(student_response.content[:1200])
        raise AssertionError("No se creó el estudiante en base de datos")

    if not student.parents.filter(id=parent.id).exists():
        raise AssertionError("El estudiante no quedó vinculado al padre")

    enrollment = Enrollment.objects.filter(student=student).order_by("-id").first()
    if not enrollment:
        raise AssertionError("No se creó la matrícula del estudiante")

    payment_post_data = {
        "student_id": str(student.id),
        "parent_id": str(parent.id),
        "payment_type": "monthly",
        "payment_method": "transfer",
        "amount": "36.00",
        "currency": "EUR",
        "payment_status": "pending",
        "due_date": "28/02/2026",
        "payment_date": "",
        "concept": "Pago smoke test",
        "reference_number": "SMOKE-REF-001",
        "observations": "",
    }

    payment_response = client.post("/payments/create/", data=payment_post_data, secure=True)

    payment = (
        Payment.objects.filter(
            student=student,
            parent=parent,
            concept="Pago smoke test",
        )
        .order_by("-id")
        .first()
    )
    if not payment:
        raise AssertionError("No se creó el pago en base de datos")

    print("SMOKE_OK")
    print(f"student_id={student.id}")
    print(f"enrollment_id={enrollment.id}; academic_year={enrollment.academic_year}")
    print(f"payment_id={payment.id}; due_date={payment.due_date.strftime('%d/%m/%Y')}")
    print(f"student_response_status={student_response.status_code}")
    print(f"payment_response_status={payment_response.status_code}")


if __name__ == "__main__":
    run()
