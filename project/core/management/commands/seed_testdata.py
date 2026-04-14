"""
Management command to populate the database with realistic test data.

Designed for the QA / testing environment so testers can exercise every
feature without having to create data manually.

Usage:
    python manage.py seed_testdata          # Full seed (idempotent)
    python manage.py seed_testdata --reset  # Wipe and re-seed
    python manage.py seed_testdata --small  # Minimal seed (fewer records)
"""

from datetime import date, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from billing.models import (
    EnrollmentType,
    Enrollment,
    Payment,
    SiteConfiguration,
    current_academic_year,
    academic_year_start_date,
)
from core.models import HistoryLog, ScheduleSlot, TodoItem
from students.models import Group, Parent, Student, StudentParent, Teacher


# ---------------------------------------------------------------------------
# Seed data constants
# ---------------------------------------------------------------------------

TEACHERS = [
    {"first_name": "Laura", "last_name": "Martinez", "email": "laura.martinez@fiveaday.test", "phone": "600100001", "admin": True},
    {"first_name": "Carlos", "last_name": "Lopez", "email": "carlos.lopez@fiveaday.test", "phone": "600100002", "admin": False},
    {"first_name": "Ana", "last_name": "Garcia", "email": "ana.garcia@fiveaday.test", "phone": "600100003", "admin": False},
]

GROUPS = [
    {"group_name": "Starters A", "color": "#6366f1", "teacher_email": "laura.martinez@fiveaday.test"},
    {"group_name": "Starters B", "color": "#8b5cf6", "teacher_email": "laura.martinez@fiveaday.test"},
    {"group_name": "Movers", "color": "#06b6d4", "teacher_email": "carlos.lopez@fiveaday.test"},
    {"group_name": "Flyers", "color": "#10b981", "teacher_email": "carlos.lopez@fiveaday.test"},
    {"group_name": "Adults", "color": "#f59e0b", "teacher_email": "ana.garcia@fiveaday.test"},
]

PARENTS = [
    {"first_name": "Maria", "last_name": "Fernandez", "dni": "12345678A", "phone": "600200001", "email": "maria.fernandez@test.com", "iban": "ES1234567890123456789012"},
    {"first_name": "Pedro", "last_name": "Sanchez", "dni": "23456789B", "phone": "600200002", "email": "pedro.sanchez@test.com", "iban": "ES2345678901234567890123"},
    {"first_name": "Carmen", "last_name": "Ruiz", "dni": "34567890C", "phone": "600200003", "email": "carmen.ruiz@test.com", "iban": "ES3456789012345678901234"},
    {"first_name": "Jose", "last_name": "Moreno", "dni": "45678901D", "phone": "600200004", "email": "jose.moreno@test.com", "iban": "ES4567890123456789012345"},
    {"first_name": "Elena", "last_name": "Navarro", "dni": "56789012E", "phone": "600200005", "email": "elena.navarro@test.com", "iban": "ES5678901234567890123456"},
    {"first_name": "Francisco", "last_name": "Romero", "dni": "67890123F", "phone": "600200006", "email": "francisco.romero@test.com", "iban": "ES6789012345678901234567"},
]

# Children: (first, last, birth_date, gender, group_name, parent_dnis, school)
CHILDREN = [
    ("Lucia", "Fernandez", date(2016, 3, 15), "f", "Starters A", ["12345678A"], "CEIP Parque Sur"),
    ("Pablo", "Fernandez", date(2018, 7, 22), "m", "Starters B", ["12345678A"], "CEIP Parque Sur"),
    ("Sofia", "Sanchez", date(2015, 11, 8), "f", "Movers", ["23456789B"], "CEIP Cristobal Valera"),
    ("Daniel", "Sanchez", date(2017, 1, 30), "m", "Starters A", ["23456789B"], "CEIP Cristobal Valera"),
    ("Martina", "Ruiz", date(2014, 5, 12), "f", "Flyers", ["34567890C"], "Colegio Compania de Maria"),
    ("Hugo", "Ruiz", date(2016, 9, 3), "m", "Movers", ["34567890C"], "Colegio Compania de Maria"),
    ("Valeria", "Moreno", date(2017, 4, 18), "f", "Starters A", ["45678901D"], "CEIP Villacerrada"),
    ("Alejandro", "Moreno", date(2015, 12, 1), "m", "Flyers", ["45678901D"], "CEIP Villacerrada"),
    ("Emma", "Navarro", date(2016, 8, 25), "f", "Starters B", ["56789012E"], "CEIP Benjamin Palencia"),
    ("Leo", "Navarro", date(2019, 2, 14), "m", "Starters A", ["56789012E"], "CEIP Benjamin Palencia"),
    ("Alba", "Romero", date(2014, 10, 7), "f", "Flyers", ["67890123F"], "Colegio Sabina Mora"),
    ("Adrian", "Romero", date(2017, 6, 20), "m", "Movers", ["67890123F"], "Colegio Sabina Mora"),
]

# Adults: (first, last, birth_date, gender, email, phone)
ADULTS = [
    ("Isabel", "Torres", date(1985, 3, 10), "f", "isabel.torres@test.com", "600300001"),
    ("Miguel", "Serrano", date(1990, 8, 22), "m", "miguel.serrano@test.com", "600300002"),
    ("Rosa", "Diaz", date(1978, 12, 5), "f", "rosa.diaz@test.com", "600300003"),
]

# Enrollment types that must exist (seeded by the old migration but needed here)
ENROLLMENT_TYPES = [
    {"name": "monthly", "display_name": "Monthly", "base_ft": "54.00", "base_pt": "36.00"},
    {"name": "quarterly", "display_name": "Quarterly", "base_ft": "162.00", "base_pt": "108.00"},
    {"name": "adults", "display_name": "Adults", "base_ft": "60.00", "base_pt": "60.00"},
]


class Command(BaseCommand):
    help = "Populate the database with realistic test data for QA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete ALL existing data before seeding.",
        )
        parser.add_argument(
            "--small",
            action="store_true",
            help="Create a smaller dataset (fewer students and payments).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        # Check if data already exists
        if Student.objects.exists():
            self.stdout.write(self.style.WARNING(
                "Database already has students. Use --reset to wipe and re-seed."
            ))
            return

        small = options["small"]
        self.stdout.write("Seeding test data...")

        self._seed_config()
        self._seed_enrollment_types()
        teachers = self._seed_teachers()
        groups = self._seed_groups(teachers)
        parents = self._seed_parents()
        children = self._seed_children(groups, parents, small)
        adults = self._seed_adults(groups)
        self._seed_enrollments_and_payments(children + adults, parents, small)
        self._seed_schedule(groups)
        self._seed_todos()
        self._seed_history()
        self._seed_inactive_student(groups, parents)

        total = Student.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {total} students, "
            f"{Parent.objects.count()} parents, "
            f"{Enrollment.objects.count()} enrollments, "
            f"{Payment.objects.count()} payments."
        ))

    # ------------------------------------------------------------------

    def _reset(self):
        self.stdout.write(self.style.WARNING("Deleting all data..."))
        HistoryLog.objects.all().delete()
        TodoItem.objects.all().delete()
        ScheduleSlot.objects.all().delete()
        Payment.objects.all().delete()
        Enrollment.objects.all().delete()
        StudentParent.objects.all().delete()
        Student.objects.all().delete()
        Parent.objects.all().delete()
        Group.objects.all().delete()
        Teacher.objects.all().delete()
        EnrollmentType.objects.all().delete()
        self.stdout.write("  All data deleted.")

    def _seed_config(self):
        SiteConfiguration.get_config()
        self.stdout.write("  Site configuration ready.")

    def _seed_enrollment_types(self):
        for et in ENROLLMENT_TYPES:
            EnrollmentType.objects.get_or_create(
                name=et["name"],
                defaults={
                    "display_name": et["display_name"],
                    "base_amount_full_time": Decimal(et["base_ft"]),
                    "base_amount_part_time": Decimal(et["base_pt"]),
                },
            )
        self.stdout.write(f"  {len(ENROLLMENT_TYPES)} enrollment types.")

    def _seed_teachers(self):
        result = {}
        for t in TEACHERS:
            obj, _ = Teacher.objects.get_or_create(
                email=t["email"],
                defaults=t,
            )
            result[t["email"]] = obj
        self.stdout.write(f"  {len(result)} teachers.")
        return result

    def _seed_groups(self, teachers):
        result = {}
        for g in GROUPS:
            obj, _ = Group.objects.get_or_create(
                group_name=g["group_name"],
                defaults={
                    "color": g["color"],
                    "teacher": teachers[g["teacher_email"]],
                },
            )
            result[g["group_name"]] = obj
        self.stdout.write(f"  {len(result)} groups.")
        return result

    def _seed_parents(self):
        result = {}
        for p in PARENTS:
            obj, _ = Parent.objects.get_or_create(
                dni=p["dni"],
                defaults=p,
            )
            result[p["dni"]] = obj
        self.stdout.write(f"  {len(result)} parents.")
        return result

    def _seed_children(self, groups, parents, small):
        data = CHILDREN[:6] if small else CHILDREN
        students = []
        for first, last, bdate, gender, group_name, parent_dnis, school in data:
            student, created = Student.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={
                    "birth_date": bdate,
                    "gender": gender,
                    "group": groups[group_name],
                    "school": school,
                    "gdpr_signed": True,
                },
            )
            if created:
                for dni in parent_dnis:
                    StudentParent.objects.get_or_create(
                        student=student,
                        parent=parents[dni],
                    )
            students.append(student)
        self.stdout.write(f"  {len(students)} child students.")
        return students

    def _seed_adults(self, groups):
        adult_group = groups.get("Adults")
        students = []
        for first, last, bdate, gender, email, phone in ADULTS:
            student, _ = Student.objects.get_or_create(
                first_name=first,
                last_name=last,
                defaults={
                    "birth_date": bdate,
                    "gender": gender,
                    "is_adult": True,
                    "email": email,
                    "phone": phone,
                    "group": adult_group,
                    "gdpr_signed": True,
                },
            )
            students.append(student)
        self.stdout.write(f"  {len(students)} adult students.")
        return students

    def _seed_enrollments_and_payments(self, students, parents, small):
        acad_year = current_academic_year()
        start_year = int(acad_year.split("-")[0])
        sept_start = academic_year_start_date(start_year)

        monthly_type = EnrollmentType.objects.get(name="monthly")
        quarterly_type = EnrollmentType.objects.get(name="quarterly")
        adults_type = EnrollmentType.objects.get(name="adults")

        today = date.today()
        enrollment_count = 0
        payment_count = 0

        for i, student in enumerate(students):
            # Decide enrollment type
            if student.is_adult:
                etype = adults_type
                schedule = "adult_group"
                modality = "monthly"
            elif i % 5 == 0:
                etype = quarterly_type
                schedule = "full_time"
                modality = "quarterly"
            else:
                etype = monthly_type
                schedule = "full_time" if i % 3 != 0 else "part_time"
                modality = "monthly"

            base = (
                etype.base_amount_full_time
                if schedule == "full_time"
                else etype.base_amount_part_time
            )

            enrollment, created = Enrollment.objects.get_or_create(
                student=student,
                status="active",
                defaults={
                    "enrollment_type": etype,
                    "enrollment_period_start": sept_start,
                    "enrollment_period_end": date(start_year + 1, 6, 30),
                    "academic_year": acad_year,
                    "schedule_type": schedule,
                    "payment_modality": modality,
                    "enrollment_amount": base,
                    "final_amount": base,
                    "enrollment_date": sept_start,
                },
            )
            if not created:
                continue
            enrollment_count += 1

            # Parent for child payments
            parent = None
            if not student.is_adult:
                sp = StudentParent.objects.filter(student=student).first()
                parent = sp.parent if sp else None

            # Generate monthly payments Sep → current month
            if modality == "monthly":
                month_fee = (
                    Decimal("54.00") if schedule == "full_time"
                    else Decimal("36.00") if schedule == "part_time"
                    else Decimal("60.00")
                )
                for m in range(9, 13):  # Sep-Dec
                    due = date(start_year, m, 5)
                    if due > today:
                        break
                    status = "completed" if due < today - timedelta(days=15) else "pending"
                    Payment.objects.create(
                        student=student,
                        enrollment=enrollment,
                        parent=parent,
                        payment_type="monthly",
                        amount=month_fee,
                        due_date=due,
                        payment_status=status,
                        payment_date=due if status == "completed" else None,
                        concept=f"Monthly fee — {date(start_year, m, 1):%B %Y}",
                    )
                    payment_count += 1

                for m in range(1, 7):  # Jan-Jun
                    due = date(start_year + 1, m, 5)
                    if due > today:
                        break
                    status = "completed" if due < today - timedelta(days=15) else "pending"
                    Payment.objects.create(
                        student=student,
                        enrollment=enrollment,
                        parent=parent,
                        payment_type="monthly",
                        amount=month_fee,
                        due_date=due,
                        payment_status=status,
                        payment_date=due if status == "completed" else None,
                        concept=f"Monthly fee — {date(start_year + 1, m, 1):%B %Y}",
                    )
                    payment_count += 1

            # Quarterly payments
            elif modality == "quarterly":
                q_amount = base
                quarters = [
                    (date(start_year, 10, 5), "Q1 Oct-Dec"),
                    (date(start_year + 1, 1, 5), "Q2 Jan-Mar"),
                    (date(start_year + 1, 4, 5), "Q3 Apr-Jun"),
                ]
                for due, label in quarters:
                    if due > today:
                        break
                    status = "completed" if due < today - timedelta(days=15) else "pending"
                    Payment.objects.create(
                        student=student,
                        enrollment=enrollment,
                        parent=parent,
                        payment_type="quarterly",
                        amount=q_amount,
                        due_date=due,
                        payment_status=status,
                        payment_date=due if status == "completed" else None,
                        concept=f"Quarterly fee — {label} {acad_year}",
                    )
                    payment_count += 1

            # Enrollment fee payment
            Payment.objects.create(
                student=student,
                enrollment=enrollment,
                parent=parent,
                payment_type="enrollment",
                amount=Decimal("40.00") if not student.is_adult else Decimal("20.00"),
                due_date=sept_start,
                payment_status="completed",
                payment_date=sept_start,
                concept=f"Enrollment fee — {acad_year}",
            )
            payment_count += 1

        self.stdout.write(f"  {enrollment_count} enrollments, {payment_count} payments.")

    def _seed_schedule(self, groups):
        slots_created = 0
        group_list = [g for name, g in groups.items() if name != "Adults"]
        for row in range(3):
            for day in range(5):  # Mon-Fri
                for col in range(2):
                    idx = (row * 10 + day * 2 + col) % len(group_list)
                    _, created = ScheduleSlot.objects.get_or_create(
                        row=row, day=day, col=col,
                        defaults={"group": group_list[idx]},
                    )
                    if created:
                        slots_created += 1
        self.stdout.write(f"  {slots_created} schedule slots.")

    def _seed_todos(self):
        today = date.today()
        todos = [
            ("Review pending payments for this month", today + timedelta(days=3)),
            ("Send payment reminders to parents", today + timedelta(days=7)),
            ("Prepare Fun Friday activities", today + timedelta(days=5)),
            ("Update student contact information", today - timedelta(days=2)),  # overdue
        ]
        count = 0
        for text, due in todos:
            _, created = TodoItem.objects.get_or_create(text=text, defaults={"due_date": due})
            if created:
                count += 1
        self.stdout.write(f"  {count} todo items.")

    def _seed_history(self):
        entries = [
            ("student_enrolled", "Lucia Fernandez enrolled in Starters A"),
            ("payment_completed", "Payment received from Maria Fernandez"),
            ("email_sent", "Welcome email sent to maria.fernandez@test.com"),
            ("config_updated", "Site configuration updated by admin"),
            ("teacher_created", "Teacher Laura Martinez added"),
        ]
        for action, msg in entries:
            HistoryLog.log(action, msg)
        self.stdout.write(f"  {len(entries)} history entries.")

    def _seed_inactive_student(self, groups, parents):
        """One withdrawn student to test inactive filters."""
        student, created = Student.objects.get_or_create(
            first_name="Marco",
            last_name="Vega",
            defaults={
                "birth_date": date(2015, 4, 20),
                "gender": "m",
                "group": groups["Starters A"],
                "school": "CEIP Parque Sur",
                "active": False,
                "withdrawal_date": date.today() - timedelta(days=60),
                "withdrawal_reason": "Family moved to another city",
                "gdpr_signed": True,
            },
        )
        if created:
            first_parent = list(parents.values())[0]
            StudentParent.objects.get_or_create(student=student, parent=first_parent)
        self.stdout.write("  1 inactive student (Marco Vega).")
