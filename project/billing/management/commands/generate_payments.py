"""
Management command to generate automatic periodic payments.

For monthly students: creates a pending payment at the start of each month (Sep-Jun).
For quarterly students: creates a pending payment at the start of each quarter
  (Oct for Q1 covering Sep-Dec, Jan for Q2, Apr for Q3).

Usage:
    python manage.py generate_payments              # Generate for current month
    python manage.py generate_payments --month 10 --year 2025  # Specific month
    python manage.py generate_payments --dry-run    # Preview without creating
"""

from django.core.management.base import BaseCommand
from billing.models import (
    Enrollment, Payment, SiteConfiguration,
    current_academic_year,
)
from billing.services.payment_service import (
    PaymentService, MONTH_NAMES_ES, QUARTER_NAMES_ES,
)
from datetime import date


class Command(BaseCommand):
    help = 'Generate automatic periodic payments for enrolled students'

    def add_arguments(self, parser):
        parser.add_argument(
            '--month', type=int, default=None,
            help='Month to generate payments for (1-12). Defaults to current month.'
        )
        parser.add_argument(
            '--year', type=int, default=None,
            help='Year to generate payments for. Defaults to current year.'
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Preview payments that would be created without saving.'
        )

    def handle(self, *args, **options):
        today = date.today()
        month = options['month'] or today.month
        year = options['year'] or today.year
        dry_run = options['dry_run']

        config = SiteConfiguration.get_config()
        academic_year = current_academic_year(date(year, month, 1))

        enrollments = Enrollment.objects.filter(
            status='active',
            academic_year=academic_year,
        ).select_related('student', 'student__group')

        created_count = 0
        skipped_count = 0

        for enrollment in enrollments:
            student = enrollment.student
            if not student.active:
                continue

            parent = None
            if not student.is_adult:
                parent = student.parents.first()
                if not parent:
                    self.stdout.write(self.style.WARNING(
                        f"  SKIP {student.full_name}: no parent found"
                    ))
                    skipped_count += 1
                    continue

            modality = enrollment.payment_modality
            due_date = date(year, month, 1)

            if modality == 'monthly' and PaymentService.should_generate_monthly(month):
                exists = Payment.objects.filter(
                    student=student,
                    payment_type='monthly',
                    due_date__month=month,
                    due_date__year=year,
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                amount = PaymentService.calculate_monthly_amount(enrollment, config, month)
                concept = f"Mensualidad {MONTH_NAMES_ES.get(month, '')} {year}"

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] {student.full_name}: {concept} - €{amount}"
                    )
                else:
                    Payment.objects.create(
                        student=student,
                        parent=parent,
                        enrollment=enrollment,
                        payment_type='monthly',
                        payment_method='transfer',
                        amount=amount,
                        payment_status='pending',
                        due_date=due_date,
                        concept=concept,
                    )
                created_count += 1

            elif modality == 'quarterly' and PaymentService.should_generate_quarterly(month):
                exists = Payment.objects.filter(
                    student=student,
                    payment_type='quarterly',
                    due_date__month=month,
                    due_date__year=year,
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                amount = PaymentService.calculate_quarterly_amount(enrollment, config, month)
                concept = f"Trimestre {QUARTER_NAMES_ES.get(month, '')} {year}"

                if dry_run:
                    self.stdout.write(
                        f"  [DRY RUN] {student.full_name}: {concept} - €{amount}"
                    )
                else:
                    Payment.objects.create(
                        student=student,
                        parent=parent,
                        enrollment=enrollment,
                        payment_type='quarterly',
                        payment_method='transfer',
                        amount=amount,
                        payment_status='pending',
                        due_date=due_date,
                        concept=concept,
                    )
                created_count += 1
            else:
                skipped_count += 1

        prefix = "[DRY RUN] " if dry_run else ""
        self.stdout.write(self.style.SUCCESS(
            f"{prefix}Payment generation complete for {MONTH_NAMES_ES.get(month, month)} {year}: "
            f"{created_count} created, {skipped_count} skipped"
        ))
