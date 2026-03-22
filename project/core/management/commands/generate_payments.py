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
from core.models import (
    Enrollment, Payment, SiteConfiguration, Student,
    current_academic_year,
)
from core import constants
from decimal import Decimal
from datetime import date


MONTH_NAMES_ES = {
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio',
}

QUARTER_NAMES_ES = {
    10: '1er Trimestre (Sep-Dic)',
    1: '2do Trimestre (Ene-Mar)',
    4: '3er Trimestre (Abr-Jun)',
}


def get_monthly_amount(enrollment, config, month):
    """Calculate the monthly payment amount for a given enrollment."""
    if enrollment.schedule_type == 'adult_group':
        # Adults: flat rate, no discounts
        return config.adult_group_monthly_fee

    # Base fee by schedule type
    if enrollment.schedule_type == 'full_time':
        base = config.full_time_monthly_fee
    else:
        base = config.part_time_monthly_fee

    amount = base

    # Sibling discount (-5%)
    if enrollment.is_sibling_discount:
        discount = amount * (config.sibling_discount / Decimal('100'))
        amount -= discount

    # Language cheque discount (-20€ flat)
    if enrollment.has_language_cheque:
        amount -= config.language_cheque_discount

    # June discount (-20€) for students completing the year
    if month == 6:
        amount -= config.june_discount

    return max(amount, Decimal('0.01'))


def get_quarterly_amount(enrollment, config, quarter_due_month):
    """Calculate the quarterly payment amount. 3 months * monthly fee * 0.95."""
    if enrollment.schedule_type == 'adult_group':
        base = config.adult_group_monthly_fee
    elif enrollment.schedule_type == 'full_time':
        base = config.full_time_monthly_fee
    else:
        base = config.part_time_monthly_fee

    total = base * 3
    # Apply quarterly discount (-5%)
    discount = total * (config.quarterly_enrollment_discount / Decimal('100'))
    total -= discount

    return max(total, Decimal('0.01'))


def should_generate_monthly(month):
    """Monthly payments are generated for Sep through Jun."""
    return month in range(1, 7) or month in range(9, 13)


def should_generate_quarterly(month):
    """Quarterly payments are generated in Oct (Q1), Jan (Q2), Apr (Q3)."""
    return month in (10, 1, 4)


def get_due_date(month, year):
    """First day of the month as due date."""
    return date(year, month, 1)


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

        # Get all active enrollments for the current academic year
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

            # Get the parent for payment (first parent, or None for adults)
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
            due_date = get_due_date(month, year)

            if modality == 'monthly' and should_generate_monthly(month):
                # Check if payment already exists for this month
                exists = Payment.objects.filter(
                    student=student,
                    payment_type='monthly',
                    due_date__month=month,
                    due_date__year=year,
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                amount = get_monthly_amount(enrollment, config, month)
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

            elif modality == 'quarterly' and should_generate_quarterly(month):
                exists = Payment.objects.filter(
                    student=student,
                    payment_type='quarterly',
                    due_date__month=month,
                    due_date__year=year,
                ).exists()

                if exists:
                    skipped_count += 1
                    continue

                amount = get_quarterly_amount(enrollment, config, month)
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
