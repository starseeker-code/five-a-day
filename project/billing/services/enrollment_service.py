"""
Service layer for enrollment business logic.
Extracted from EnrollmentForm.create_enrollment() in forms.py.
"""
from decimal import Decimal
from datetime import date

from billing.models import (
    Enrollment, EnrollmentType, SiteConfiguration,
    current_academic_year, academic_year_start_date, academic_year_end_date,
)


class EnrollmentService:

    @staticmethod
    def create_enrollment(student, enrollment_data, is_adult=False):
        """
        Create and save an Enrollment from validated form data.

        Args:
            student: Student instance
            enrollment_data: dict with keys:
                - enrollment_plan: 'monthly_full' | 'monthly_part' | 'quarterly'
                - has_language_cheque: bool
                - is_sibling_discount: bool
                - is_special: bool
                - manual_amount: Decimal or None
            is_adult: bool

        Returns:
            Enrollment instance
        """
        config = SiteConfiguration.get_config()
        academic_year = current_academic_year()
        start_year = int(academic_year.split('-')[0])
        end_year = int(academic_year.split('-')[1])
        today = date.today()

        is_special = enrollment_data.get('is_special', False)
        manual_amount = enrollment_data.get('manual_amount')
        has_lc = enrollment_data.get('has_language_cheque', False)
        has_sibling = enrollment_data.get('is_sibling_discount', False)

        enrollment_type, base_amount, schedule_type, payment_modality = (
            EnrollmentService._resolve_plan(
                config, enrollment_data, is_adult, is_special, manual_amount
            )
        )

        discount_pct, final_amount = EnrollmentService._apply_discounts(
            config, base_amount, has_lc, has_sibling, is_adult, payment_modality
        )

        enrollment = Enrollment(
            student=student,
            enrollment_type=enrollment_type,
            enrollment_period_start=academic_year_start_date(start_year),
            enrollment_period_end=academic_year_end_date(end_year),
            academic_year=academic_year,
            schedule_type=schedule_type,
            payment_modality=payment_modality,
            has_language_cheque=has_lc,
            is_sibling_discount=has_sibling,
            enrollment_amount=base_amount,
            discount_percentage=discount_pct,
            final_amount=final_amount,
            status='active',
            enrollment_date=today,
        )
        enrollment.save()
        return enrollment

    @staticmethod
    def _resolve_plan(config, data, is_adult, is_special, manual_amount):
        """
        Determine enrollment type, base amount, schedule type, and payment modality.
        Returns: (enrollment_type, base_amount, schedule_type, payment_modality)
        """
        if is_adult:
            if is_special and manual_amount:
                enrollment_type = EnrollmentType.objects.get(name='special')
                return enrollment_type, manual_amount, 'adult_group', 'monthly'
            else:
                enrollment_type = EnrollmentType.objects.get(name='adults')
                return enrollment_type, config.adult_group_monthly_fee, 'adult_group', 'monthly'

        plan = data.get('enrollment_plan', 'monthly_full')

        if is_special and manual_amount:
            enrollment_type = EnrollmentType.objects.get(name='special')
            if plan == 'monthly_full':
                return enrollment_type, manual_amount, 'full_time', 'monthly'
            elif plan == 'monthly_part':
                return enrollment_type, manual_amount, 'part_time', 'monthly'
            else:
                return enrollment_type, manual_amount, 'full_time', 'quarterly'

        if plan == 'monthly_full':
            et = EnrollmentType.objects.get(name='monthly')
            return et, config.full_time_monthly_fee, 'full_time', 'monthly'
        elif plan == 'monthly_part':
            et = EnrollmentType.objects.get(name='monthly')
            return et, config.part_time_monthly_fee, 'part_time', 'monthly'
        elif plan == 'quarterly':
            et = EnrollmentType.objects.get(name='quarterly')
            quarterly_base = config.full_time_monthly_fee * 3
            quarterly_discount = config.quarterly_enrollment_discount
            base_amount = quarterly_base * (1 - quarterly_discount / 100)
            return et, base_amount, 'full_time', 'quarterly'
        else:
            et = EnrollmentType.objects.get(name='monthly')
            return et, config.full_time_monthly_fee, 'full_time', 'monthly'

    @staticmethod
    def _apply_discounts(config, base_amount, has_lc, has_sibling, is_adult, payment_modality):
        """
        Apply discounts and return (discount_pct, final_amount).
        """
        discount_pct = Decimal('0')
        final_amount = base_amount

        if has_sibling and not is_adult:
            discount_pct += config.sibling_discount
            final_amount = base_amount * (1 - config.sibling_discount / 100)

        if has_lc and not is_adult:
            lc_amount = config.language_cheque_discount
            if payment_modality == 'quarterly':
                lc_amount = lc_amount * 3
            final_amount = final_amount - lc_amount

        if final_amount < Decimal('0.01'):
            final_amount = Decimal('0.01')

        return discount_pct, final_amount
