"""
Service layer for payment business logic.
Extracted from generate_payments management command and views.
"""
from decimal import Decimal
from datetime import date

from billing.models import Enrollment, Payment, SiteConfiguration


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


class PaymentService:

    @staticmethod
    def calculate_monthly_amount(enrollment, config, month):
        """Calculate the monthly payment amount for a given enrollment."""
        if enrollment.schedule_type == 'adult_group':
            return config.adult_group_monthly_fee

        if enrollment.schedule_type == 'full_time':
            base = config.full_time_monthly_fee
        else:
            base = config.part_time_monthly_fee

        amount = base

        if enrollment.is_sibling_discount:
            discount = amount * (config.sibling_discount / Decimal('100'))
            amount -= discount

        if enrollment.has_language_cheque:
            amount -= config.language_cheque_discount

        if month == 6:
            amount -= config.june_discount

        return max(amount, Decimal('0.01'))

    @staticmethod
    def calculate_quarterly_amount(enrollment, config, quarter_due_month):
        """Calculate the quarterly payment amount (3 months * monthly fee - 5%)."""
        if enrollment.schedule_type == 'adult_group':
            base = config.adult_group_monthly_fee
        elif enrollment.schedule_type == 'full_time':
            base = config.full_time_monthly_fee
        else:
            base = config.part_time_monthly_fee

        total = base * 3
        discount = total * (config.quarterly_enrollment_discount / Decimal('100'))
        total -= discount

        return max(total, Decimal('0.01'))

    @staticmethod
    def complete_payment(payment_id):
        """Mark a payment as completed. Returns the updated Payment."""
        payment = Payment.objects.select_related('student').get(id=payment_id)
        payment.payment_status = 'completed'
        payment.payment_date = date.today()
        payment.save()
        return payment

    @staticmethod
    def should_generate_monthly(month):
        """Monthly payments are generated for Sep through Jun."""
        return month in range(1, 7) or month in range(9, 13)

    @staticmethod
    def should_generate_quarterly(month):
        """Quarterly payments are generated in Oct (Q1), Jan (Q2), Apr (Q3)."""
        return month in (10, 1, 4)

    @staticmethod
    def get_payment_statistics(month, year):
        """Calculate payment statistics for a given month/year."""
        from django.db.models import Sum

        pending = Payment.objects.filter(
            payment_status='pending',
            due_date__month=month,
            due_date__year=year,
        )
        completed = Payment.objects.filter(
            payment_status='completed',
            payment_date__month=month,
            payment_date__year=year,
        )

        pending_total = pending.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        completed_total = completed.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

        return {
            'pending_count': pending.count(),
            'pending_total': pending_total,
            'completed_count': completed.count(),
            'completed_total': completed_total,
            'expected_total': pending_total + completed_total,
        }
