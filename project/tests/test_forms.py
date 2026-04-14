"""Tests for billing.forms — EnrollmentForm validation."""

import pytest

from billing.forms import EnrollmentForm

pytestmark = pytest.mark.django_db


class TestEnrollmentFormValidation:
    def test_valid_monthly_full(self):
        form = EnrollmentForm(data={"enrollment_plan": "monthly_full"})
        assert form.is_valid()

    def test_valid_quarterly(self):
        form = EnrollmentForm(data={"enrollment_plan": "quarterly"})
        assert form.is_valid()

    def test_special_without_amount_fails(self):
        form = EnrollmentForm(data={"is_special": True})
        assert not form.is_valid()
        assert "Debes especificar un precio manual" in str(form.errors)

    def test_special_with_amount_passes(self):
        form = EnrollmentForm(data={"is_special": True, "manual_amount": "25.00"})
        assert form.is_valid()

    def test_manual_amount_below_minimum_fails(self):
        form = EnrollmentForm(data={"is_special": True, "manual_amount": "0.00"})
        assert not form.is_valid()

    def test_sibling_discount_checkbox(self):
        form = EnrollmentForm(data={"enrollment_plan": "monthly_full", "is_sibling_discount": True})
        assert form.is_valid()
        assert form.cleaned_data["is_sibling_discount"] is True

    def test_language_cheque_checkbox(self):
        form = EnrollmentForm(data={"enrollment_plan": "monthly_full", "has_language_cheque": True})
        assert form.is_valid()
        assert form.cleaned_data["has_language_cheque"] is True


class TestEnrollmentFormCreateEnrollment:
    def test_creates_enrollment(self, student, enrollment_type_monthly, site_config):
        form = EnrollmentForm(data={"enrollment_plan": "monthly_full"})
        assert form.is_valid()
        enrollment = form.create_enrollment(student, is_adult=False)
        assert enrollment.student == student
        assert enrollment.status == "active"
        assert enrollment.schedule_type == "full_time"

    def test_creates_adult_enrollment(self, adult_student, enrollment_type_adults, site_config):
        form = EnrollmentForm(data={"enrollment_plan": "monthly_full"})
        assert form.is_valid()
        enrollment = form.create_enrollment(adult_student, is_adult=True)
        assert enrollment.student == adult_student
        assert enrollment.schedule_type == "adult_group"
