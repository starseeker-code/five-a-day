"""Tests for core.services — business logic layer."""
import pytest
from decimal import Decimal
from datetime import date

from billing.models import Enrollment, Payment, SiteConfiguration
from billing.services.enrollment_service import EnrollmentService
from billing.services.payment_service import PaymentService
from billing.services.pricing_service import PricingService


# ── PricingService ───────────────────────────────────────────────────────────


class TestPricingService:
    def test_get_config(self, site_config):
        config = PricingService.get_config()
        assert config.pk == 1

    def test_get_monthly_fee_full_time(self, site_config):
        assert PricingService.get_monthly_fee("full_time") == Decimal("54.00")

    def test_get_monthly_fee_part_time(self, site_config):
        assert PricingService.get_monthly_fee("part_time") == Decimal("36.00")

    def test_get_monthly_fee_adult(self, site_config):
        assert PricingService.get_monthly_fee("adult_group") == Decimal("60.00")

    def test_get_enrollment_fee_child(self, site_config):
        assert PricingService.get_enrollment_fee(is_adult=False) == Decimal("40.00")

    def test_get_enrollment_fee_adult(self, site_config):
        assert PricingService.get_enrollment_fee(is_adult=True) == Decimal("20.00")

    def test_calculate_quarterly_price(self, site_config):
        # 54 * 3 = 162, minus 5% = 153.90
        result = PricingService.calculate_quarterly_price()
        assert result == Decimal("153.90")


# ── EnrollmentService ────────────────────────────────────────────────────────


class TestEnrollmentService:
    def test_create_monthly_full_time(
        self, student, site_config, enrollment_type_monthly
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        assert enrollment.status == "active"
        assert enrollment.schedule_type == "full_time"
        assert enrollment.payment_modality == "monthly"
        assert enrollment.final_amount == Decimal("54.00")

    def test_create_monthly_part_time(
        self, student, site_config, enrollment_type_monthly
    ):
        data = {
            "enrollment_plan": "monthly_part",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        assert enrollment.schedule_type == "part_time"
        assert enrollment.final_amount == Decimal("36.00")

    def test_create_quarterly(
        self, student, site_config, enrollment_type_quarterly
    ):
        data = {
            "enrollment_plan": "quarterly",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        assert enrollment.payment_modality == "quarterly"
        assert enrollment.final_amount == Decimal("153.90")

    def test_sibling_discount_applied(
        self, student, site_config, enrollment_type_monthly
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": False,
            "is_sibling_discount": True,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        # 54 * (1 - 5/100) = 51.30
        assert enrollment.final_amount == Decimal("51.30")
        assert enrollment.is_sibling_discount is True

    def test_language_cheque_discount_applied(
        self, student, site_config, enrollment_type_monthly
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": True,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        # 54 - 20 = 34
        assert enrollment.final_amount == Decimal("34.00")
        assert enrollment.has_language_cheque is True

    def test_both_discounts_combined(
        self, student, site_config, enrollment_type_monthly
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": True,
            "is_sibling_discount": True,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        # Base: 54, sibling: 54*(1-0.05) = 51.30, then LC: 51.30 - 20 = 31.30
        assert enrollment.final_amount == Decimal("31.30")

    def test_special_enrollment_with_manual_amount(
        self, student, site_config, enrollment_type_special
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": True,
            "manual_amount": Decimal("25.00"),
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        assert enrollment.final_amount == Decimal("25.00")
        assert enrollment.enrollment_type.name == "special"

    def test_adult_enrollment(
        self, adult_student, site_config, enrollment_type_adults
    ):
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(
            adult_student, data, is_adult=True
        )
        assert enrollment.schedule_type == "adult_group"
        assert enrollment.final_amount == Decimal("60.00")

    def test_minimum_amount_enforced(
        self, student, site_config, enrollment_type_monthly
    ):
        # Force a scenario where discounts exceed base amount
        config = site_config
        config.language_cheque_discount = Decimal("100.00")
        config.save()

        data = {
            "enrollment_plan": "monthly_part",  # 36.00
            "has_language_cheque": True,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        enrollment = EnrollmentService.create_enrollment(student, data)
        assert enrollment.final_amount == Decimal("0.01")


# ── PaymentService ───────────────────────────────────────────────────────────


class TestPaymentService:
    def test_calculate_monthly_amount_full_time(self, active_enrollment, site_config):
        amount = PaymentService.calculate_monthly_amount(
            active_enrollment, site_config, month=10
        )
        assert amount == Decimal("54.00")

    def test_calculate_monthly_with_sibling_discount(
        self, active_enrollment, site_config
    ):
        active_enrollment.is_sibling_discount = True
        active_enrollment.save()
        amount = PaymentService.calculate_monthly_amount(
            active_enrollment, site_config, month=10
        )
        # 54 - (54 * 5/100) = 54 - 2.70 = 51.30
        assert amount == Decimal("51.30")

    def test_calculate_monthly_with_language_cheque(
        self, active_enrollment, site_config
    ):
        active_enrollment.has_language_cheque = True
        active_enrollment.save()
        amount = PaymentService.calculate_monthly_amount(
            active_enrollment, site_config, month=10
        )
        # 54 - 20 = 34
        assert amount == Decimal("34.00")

    def test_calculate_monthly_june_discount(self, active_enrollment, site_config):
        amount = PaymentService.calculate_monthly_amount(
            active_enrollment, site_config, month=6
        )
        # 54 - 20 (june discount) = 34
        assert amount == Decimal("34.00")

    def test_calculate_quarterly_amount(self, active_enrollment, site_config):
        amount = PaymentService.calculate_quarterly_amount(
            active_enrollment, site_config, quarter_due_month=10
        )
        # 54 * 3 = 162, minus 5% = 153.90
        assert amount == Decimal("153.90")

    def test_complete_payment(self, pending_payment):
        payment = PaymentService.complete_payment(pending_payment.id)
        assert payment.payment_status == "completed"
        assert payment.payment_date == date.today()

    def test_should_generate_monthly(self):
        # Academic months: Sep-Jun (9,10,11,12,1,2,3,4,5,6)
        assert PaymentService.should_generate_monthly(9) is True
        assert PaymentService.should_generate_monthly(6) is True
        assert PaymentService.should_generate_monthly(7) is False
        assert PaymentService.should_generate_monthly(8) is False

    def test_should_generate_quarterly(self):
        assert PaymentService.should_generate_quarterly(10) is True
        assert PaymentService.should_generate_quarterly(1) is True
        assert PaymentService.should_generate_quarterly(4) is True
        assert PaymentService.should_generate_quarterly(2) is False


# ── EnrollmentService error handling ────────────────────────────────────────


class TestEnrollmentServiceErrors:
    def test_missing_enrollment_type_raises_value_error(self, student, site_config):
        """When enrollment types don't exist in DB, service should raise ValueError."""
        data = {
            "enrollment_plan": "monthly_full",
            "has_language_cheque": False,
            "is_sibling_discount": False,
            "is_special": False,
            "manual_amount": None,
        }
        # No enrollment types created — should raise ValueError
        with pytest.raises(ValueError, match="EnrollmentType"):
            EnrollmentService.create_enrollment(student, data)

    def test_payment_statistics(self, site_config, pending_payment, completed_payment):
        stats = PaymentService.get_payment_statistics(
            month=pending_payment.due_date.month,
            year=pending_payment.due_date.year,
        )
        assert stats["pending_count"] >= 1
        assert isinstance(stats["pending_total"], Decimal)
