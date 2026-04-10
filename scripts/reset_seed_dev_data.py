from datetime import date, timedelta
from decimal import Decimal
import os
import random
import sys

from django.conf import settings
from django.db import transaction
from django.db.models import Count

from core.models import (
    SiteConfiguration,
    EnrollmentType,
    Teacher,
    Group,
    Parent,
    Student,
    Enrollment,
    Payment,
)


def _check_environment():
    """Abort if running in production — this script destroys ALL data."""
    env = os.getenv("DJANGO_ENV", "").lower()
    debug = getattr(settings, "DEBUG", False)
    if env == "production" or not debug:
        print(
            "ABORT: reset_seed_dev_data.py cannot run in production "
            "(DJANGO_ENV='production' or DEBUG=False). "
            "Set DJANGO_ENV=development and DEBUG=True to proceed."
        )
        sys.exit(1)


_check_environment()


random.seed(20260227)

FIRST_NAMES = [
    "Lucas", "Martina", "Hugo", "Sofía", "Daniel", "Paula", "Alejandro", "Valeria",
    "Mateo", "Claudia", "Pablo", "Nora", "Diego", "Alba", "Marco", "Irene",
    "Adrián", "Elena", "Javier", "Lucía", "Álvaro", "Carla", "Raúl", "Marta",
    "Bruno", "Noa", "Víctor", "Aitana", "Gonzalo", "Sara", "Mario", "Lola",
    "Eric", "Naiara", "Rubén", "Inés", "Samuel", "Leire", "Gael", "Olivia",
]

LAST_NAMES = [
    "García", "Martínez", "López", "Sánchez", "Pérez", "Gómez", "Fernández", "Ruiz",
    "Díaz", "Moreno", "Muñoz", "Álvarez", "Romero", "Alonso", "Navarro", "Torres",
    "Domínguez", "Vázquez", "Ramos", "Gil", "Castro", "Ortega", "Molina", "Delgado",
    "Suárez", "Santos", "Iglesias", "Reyes", "Méndez", "Cruz", "Serrano", "Flores",
]

SCHOOLS = [
    "CEIP Valle Verde", "Colegio San Martín", "IES Río Azul", "Colegio Aurora",
    "CEIP Las Acacias", "IES Sierra Norte", "Colegio Atlántico", "CEIP El Bosque",
    "Colegio Alameda", "IES Costa Sur",
]


def normalize(value: str) -> str:
    return (
        value.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def phone_for(index: int) -> str:
    return f"123{600000 + index:06d}"


def dni_for(index: int) -> str:
    letters = "TRWAGMYFPDXBNJZSQVHLCKE"
    number = 12300000 + index
    return f"{number}{letters[number % 23]}"


def email_for(first_name: str, last_name: str, index: int) -> str:
    return f"{normalize(first_name)}.{normalize(last_name)}.{index}@example.com"


def random_name(index: int):
    return FIRST_NAMES[index % len(FIRST_NAMES)], LAST_NAMES[(index * 5) % len(LAST_NAMES)]


def ensure_enrollment_types(config: SiteConfiguration):
    setup = {
        "adults": ("Adults", config.adult_group_monthly_fee, config.adult_group_monthly_fee),
        "special": ("Special", Decimal("75.00"), Decimal("55.00")),
        "languages_ticket": ("Languages Ticket", Decimal("65.00"), Decimal("45.00")),
        "monthly": ("Monthly", config.full_time_monthly_fee, config.part_time_monthly_fee),
        "half_month": ("Half-month", config.full_time_monthly_fee / 2, config.part_time_monthly_fee / 2),
        "quarterly": ("Quarterly", config.full_time_monthly_fee * 3, config.part_time_monthly_fee * 3),
    }

    for key, (display_name, full, part) in setup.items():
        EnrollmentType.objects.update_or_create(
            name=key,
            defaults={
                "display_name": display_name,
                "base_amount_full_time": full.quantize(Decimal("0.01")),
                "base_amount_part_time": part.quantize(Decimal("0.01")),
                "description": f"Tipo {display_name} (seed dev)",
                "active": True,
            },
        )


@transaction.atomic
def run_seed():
    today = date.today()
    month = today.month

    Payment.objects.all().delete()
    Enrollment.objects.all().delete()
    Student.objects.all().delete()
    Parent.objects.all().delete()
    Group.objects.all().delete()
    Teacher.objects.all().delete()

    config = SiteConfiguration.get_config()
    ensure_enrollment_types(config)
    enrollment_types = list(EnrollmentType.objects.filter(active=True).order_by("name"))

    teachers = [
        Teacher.objects.create(
            first_name=first,
            last_name=last,
            email=email_for(first, last, i + 1),
            phone=phone_for(i + 1),
            active=True,
            admin=(i == 0),
        )
        for i, (first, last) in enumerate([
            ("Laura", "Jiménez"),
            ("Carlos", "Ortega"),
            ("Ana", "Velasco"),
        ])
    ]

    group_names = [
        "Kids A1", "Kids A2", "Kids B1", "Kids B2",
        "Teens A2", "Teens B1", "Adults A2", "Adults B1",
    ]
    groups = [
        Group.objects.create(
            group_name=name,
            teacher=teachers[idx % len(teachers)],
            active=True,
        )
        for idx, name in enumerate(group_names)
    ]

    parents = []
    for idx in range(1, 75):
        f, l = random_name(idx + 100)
        parents.append(
            Parent.objects.create(
                first_name=f,
                last_name=l,
                dni=dni_for(idx),
                phone=phone_for(100 + idx),
                email=email_for(f, l, idx),
                iban=f"ES91{12300000000000000000 + idx:020d}",
            )
        )

    students = []

    sibling_families = [
        ("Serrano", ["Nora", "Leo", "Vera"]),
        ("Pascual", ["Álex", "Nerea", "Bruno"]),
    ]

    for fam_idx, (last_name, sibling_names) in enumerate(sibling_families):
        mom = Parent.objects.create(
            first_name="María" if fam_idx == 0 else "Cristina",
            last_name=last_name,
            dni=dni_for(500 + fam_idx * 2),
            phone=phone_for(500 + fam_idx * 2),
            email=email_for("Maria" if fam_idx == 0 else "Cristina", last_name, 500 + fam_idx * 2),
            iban=f"ES91{12300000000000000500 + fam_idx * 2:020d}",
        )
        dad = Parent.objects.create(
            first_name="Jorge" if fam_idx == 0 else "Iván",
            last_name=last_name,
            dni=dni_for(501 + fam_idx * 2),
            phone=phone_for(501 + fam_idx * 2),
            email=email_for("Jorge" if fam_idx == 0 else "Ivan", last_name, 501 + fam_idx * 2),
            iban=f"ES91{12300000000000000501 + fam_idx * 2:020d}",
        )

        for s_idx, s_name in enumerate(sibling_names):
            s = Student.objects.create(
                first_name=s_name,
                last_name=last_name,
                birth_date=date(today.year - (8 + s_idx + fam_idx), month, min(10 + s_idx, 28)),
                school=SCHOOLS[(s_idx + fam_idx) % len(SCHOOLS)],
                allergies="" if s_idx != 1 else "Lactosa",
                gdpr_signed=True,
                group=groups[(s_idx + fam_idx) % len(groups)],
                active=True,
            )
            s.parents.add(mom, dad)
            students.append(s)

    # 72 total students target -> 6 siblings + 66 extra
    for idx in range(1, 67):
        f, l = random_name(idx)
        b_month = month if idx <= 15 else random.randint(1, 12)
        b_day = min(1 + (idx % 27), 28)
        birth = date(today.year - random.randint(6, 18), b_month, b_day)

        s = Student.objects.create(
            first_name=f,
            last_name=l,
            birth_date=birth,
            school=SCHOOLS[idx % len(SCHOOLS)],
            allergies="Frutos secos" if idx % 9 == 0 else "",
            gdpr_signed=(idx % 5 != 0),
            group=groups[idx % len(groups)],
            active=True,
        )

        p1 = parents[idx % len(parents)]
        s.parents.add(p1)
        if idx % 6 == 0:
            p2 = parents[(idx + 13) % len(parents)]
            if p2.id != p1.id:
                s.parents.add(p2)

        students.append(s)

    enrollment_statuses = [
        "active", "active", "active", "active", "active",
        "pending", "finished", "cancelled", "suspended",
    ]

    enrollments = []
    start_year = today.year if today.month >= 9 else today.year - 1
    period_start = date(start_year, 9, 1)
    period_end = date(start_year + 1, 8, 31)

    for idx, s in enumerate(students):
        e_type = enrollment_types[idx % len(enrollment_types)]
        schedule = ["full_time", "part_time", "adult_group"][idx % 3]
        base = e_type.base_amount_full_time if schedule == "full_time" else e_type.base_amount_part_time
        discount = Decimal([0, 0, 5, 10, 15][idx % 5])
        final = (base * (Decimal("1") - discount / Decimal("100"))).quantize(Decimal("0.01"))

        enrollment = Enrollment.objects.create(
            student=s,
            enrollment_type=e_type,
            enrollment_period_start=period_start,
            enrollment_period_end=period_end,
            academic_year=f"{start_year}-{start_year+1}",
            schedule_type=schedule,
            enrollment_amount=final,
            discount_percentage=discount,
            final_amount=final,
            status=enrollment_statuses[idx % len(enrollment_statuses)],
            enrollment_date=today - timedelta(days=random.randint(0, 320)),
            notes="Seed desarrollo: dataset amplio",
        )
        enrollments.append(enrollment)

    payment_statuses = ["completed", "pending", "failed", "cancelled", "refunded"]
    payment_methods = ["cash", "transfer", "credit_card"]
    payment_types = ["enrollment", "monthly", "quarterly", "other"]
    amount_pattern = [Decimal("0.01"), Decimal("18.50"), Decimal("54.00"), Decimal("120.00"), Decimal("999.99")]

    for idx, s in enumerate(students):
        e = enrollments[idx]
        p = s.parents.first()

        for p_idx in range(4):
            status = payment_statuses[(idx + p_idx) % len(payment_statuses)]
            p_type = payment_types[(idx + p_idx) % len(payment_types)]
            p_method = payment_methods[(idx + p_idx) % len(payment_methods)]
            amount = amount_pattern[(idx + p_idx) % len(amount_pattern)]

            due = today + timedelta(days=((idx * 3 + p_idx * 7) % 90) - 40)
            paid = None
            if status in ("completed", "refunded"):
                paid = min(today, due + timedelta(days=random.randint(0, 8)))

            Payment.objects.create(
                student=s,
                enrollment=e,
                parent=p,
                payment_type=p_type,
                payment_method=p_method,
                amount=amount,
                currency="EUR",
                payment_status=status,
                due_date=due,
                payment_date=paid,
                concept=f"{p_type.capitalize()} - {s.full_name}",
                reference_number=f"REF-123-{idx:03d}-{p_idx}",
                observations="Pago generado automáticamente para QA",
            )

    status_summary = list(Payment.objects.values("payment_status").annotate(c=Count("id")).order_by("payment_status"))
    type_summary = list(Payment.objects.values("payment_type").annotate(c=Count("id")).order_by("payment_type"))
    method_summary = list(Payment.objects.values("payment_method").annotate(c=Count("id")).order_by("payment_method"))

    print("✅ Seed masivo aplicado")
    print(f"Profesores: {Teacher.objects.count()}")
    print(f"Grupos: {Group.objects.count()}")
    print(f"Padres: {Parent.objects.count()}")
    print(f"Estudiantes: {Student.objects.count()}")
    print(f"Matrículas: {Enrollment.objects.count()}")
    print(f"Pagos: {Payment.objects.count()}")
    print(f"Cumpleaños este mes: {Student.objects.filter(birth_date__month=month).count()}")
    print(f"Pendientes vencidos: {Payment.objects.filter(payment_status='pending', due_date__lt=today).count()}")
    print(f"Pendientes futuros/hoy: {Payment.objects.filter(payment_status='pending', due_date__gte=today).count()}")
    print(f"Alumnos con >=2 padres (incluye hermanos): {Student.objects.annotate(pc=Count('parents')).filter(pc__gte=2).count()}")
    print(f"Resumen status: {status_summary}")
    print(f"Resumen tipos: {type_summary}")
    print(f"Resumen métodos: {method_summary}")


run_seed()
