"""Tests for billing.constants — pure utility functions."""

from decimal import Decimal

import pytest

from billing.constants import (
    ADULT_ENROLLMENT_FEE,
    ADULT_GROUP_MONTHLY_FEE,
    CHILDREN_ENROLLMENT_FEE,
    FULL_TIME_MONTHLY_FEE,
    PART_TIME_MONTHLY_FEE,
    calculate_discount,
    get_enrollment_fee,
    get_monthly_fee_by_schedule,
)


class TestCalculateDiscount:
    def test_flat_discount(self):
        assert calculate_discount(Decimal("100"), (Decimal("10"), "flat")) == Decimal("10")

    def test_flat_discount_exceeding_base(self):
        assert calculate_discount(Decimal("5"), (Decimal("20"), "flat")) == Decimal("20")

    def test_percentage_discount(self):
        result = calculate_discount(Decimal("100"), (Decimal("5"), "percentage"))
        assert result == Decimal("5.00")

    def test_percentage_discount_large(self):
        result = calculate_discount(Decimal("200"), (Decimal("50"), "percentage"))
        assert result == Decimal("100.00")

    def test_percentage_discount_zero_base(self):
        result = calculate_discount(Decimal("0"), (Decimal("10"), "percentage"))
        assert result == Decimal("0.00")

    def test_invalid_discount_type_raises(self):
        with pytest.raises(ValueError, match="no válido"):
            calculate_discount(Decimal("100"), (Decimal("10"), "invalid"))


class TestGetMonthlyFeeBySchedule:
    def test_full_time(self):
        assert get_monthly_fee_by_schedule("full_time") == FULL_TIME_MONTHLY_FEE

    def test_part_time(self):
        assert get_monthly_fee_by_schedule("part_time") == PART_TIME_MONTHLY_FEE

    def test_adult_group(self):
        assert get_monthly_fee_by_schedule("adult_group") == ADULT_GROUP_MONTHLY_FEE

    def test_unknown_defaults_to_full_time(self):
        assert get_monthly_fee_by_schedule("nonexistent") == FULL_TIME_MONTHLY_FEE


class TestGetEnrollmentFee:
    def test_child(self):
        assert get_enrollment_fee(is_adult=False) == CHILDREN_ENROLLMENT_FEE

    def test_adult(self):
        assert get_enrollment_fee(is_adult=True) == ADULT_ENROLLMENT_FEE

    def test_default_is_child(self):
        assert get_enrollment_fee() == CHILDREN_ENROLLMENT_FEE
