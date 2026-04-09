import pytest
from decimal import Decimal
from datetime import date

from students.models import Teacher, Group, Parent, Student, StudentParent
from billing.models import SiteConfiguration, EnrollmentType, Enrollment, Payment
from core.models import TodoItem, HistoryLog


@pytest.fixture
def site_config(db):
    """Create or get the singleton SiteConfiguration."""
    return SiteConfiguration.get_config()


@pytest.fixture
def teacher(db):
    return Teacher.objects.create(
        first_name="Ana",
        last_name="García",
        email="ana@fiveaday.test",
        phone="600111222",
        active=True,
    )


@pytest.fixture
def group(db, teacher):
    return Group.objects.create(
        group_name="Group A",
        color="#8b5cf6",
        teacher=teacher,
        active=True,
    )


@pytest.fixture
def parent(db):
    return Parent.objects.create(
        first_name="María",
        last_name="López",
        dni="12345678A",
        phone="600333444",
        email="maria@test.com",
        iban="ES1234567890123456789012",
    )


@pytest.fixture
def second_parent(db):
    return Parent.objects.create(
        first_name="Pedro",
        last_name="Martín",
        dni="87654321B",
        phone="600555666",
        email="pedro@test.com",
    )


@pytest.fixture
def student(db, group):
    return Student.objects.create(
        first_name="Lucas",
        last_name="López García",
        birth_date=date(2018, 5, 15),
        school="CEIP Test",
        gdpr_signed=True,
        group=group,
        active=True,
    )


@pytest.fixture
def adult_student(db, group):
    return Student.objects.create(
        first_name="Carlos",
        last_name="Ruiz",
        birth_date=date(1990, 3, 10),
        is_adult=True,
        email="carlos@test.com",
        phone="600777888",
        gdpr_signed=True,
        group=group,
        active=True,
    )


@pytest.fixture
def student_with_parent(db, student, parent):
    StudentParent.objects.create(student=student, parent=parent)
    return student


@pytest.fixture
def enrollment_type_monthly(db):
    et, _ = EnrollmentType.objects.get_or_create(
        name="monthly",
        defaults={
            "display_name": "Mensual",
            "base_amount_full_time": Decimal("54.00"),
            "base_amount_part_time": Decimal("36.00"),
            "active": True,
        },
    )
    return et


@pytest.fixture
def enrollment_type_quarterly(db):
    et, _ = EnrollmentType.objects.get_or_create(
        name="quarterly",
        defaults={
            "display_name": "Trimestral",
            "base_amount_full_time": Decimal("153.90"),
            "base_amount_part_time": Decimal("102.60"),
            "active": True,
        },
    )
    return et


@pytest.fixture
def enrollment_type_adults(db):
    et, _ = EnrollmentType.objects.get_or_create(
        name="adults",
        defaults={
            "display_name": "Adultos",
            "base_amount_full_time": Decimal("60.00"),
            "base_amount_part_time": Decimal("60.00"),
            "active": True,
        },
    )
    return et


@pytest.fixture
def enrollment_type_special(db):
    et, _ = EnrollmentType.objects.get_or_create(
        name="special",
        defaults={
            "display_name": "Especial",
            "base_amount_full_time": Decimal("0.01"),
            "base_amount_part_time": Decimal("0.01"),
            "active": True,
        },
    )
    return et


@pytest.fixture
def active_enrollment(db, student, enrollment_type_monthly, site_config):
    return Enrollment.objects.create(
        student=student,
        enrollment_type=enrollment_type_monthly,
        enrollment_period_start=date(2025, 9, 15),
        enrollment_period_end=date(2026, 6, 27),
        academic_year="2025-2026",
        schedule_type="full_time",
        payment_modality="monthly",
        enrollment_amount=Decimal("54.00"),
        discount_percentage=Decimal("0.00"),
        final_amount=Decimal("54.00"),
        status="active",
        enrollment_date=date(2025, 9, 1),
    )


@pytest.fixture
def pending_payment(db, student, parent, active_enrollment):
    return Payment.objects.create(
        student=student,
        parent=parent,
        enrollment=active_enrollment,
        payment_type="monthly",
        payment_method="transfer",
        amount=Decimal("54.00"),
        payment_status="pending",
        due_date=date(2025, 10, 1),
        concept="Mensualidad Octubre 2025",
    )


@pytest.fixture
def completed_payment(db, student, parent, active_enrollment):
    return Payment.objects.create(
        student=student,
        parent=parent,
        enrollment=active_enrollment,
        payment_type="monthly",
        payment_method="transfer",
        amount=Decimal("54.00"),
        payment_status="completed",
        due_date=date(2025, 9, 1),
        payment_date=date(2025, 9, 5),
        concept="Mensualidad Septiembre 2025",
    )


@pytest.fixture
def authenticated_client(client):
    """A Django test client with session-based auth (matching SimpleAuthMiddleware)."""
    session = client.session
    session["is_authenticated"] = True
    session["username"] = "testuser"
    session.save()
    return client
