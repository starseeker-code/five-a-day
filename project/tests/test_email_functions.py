"""Tests for comms.services.email_functions — convenience email wrappers."""

from unittest.mock import patch

import pytest

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def mock_email_service():
    """Mock the global email_service so no real emails are sent."""
    with patch("comms.services.email_functions.email_service") as mock_svc:
        mock_svc.send_email.return_value = True
        yield mock_svc


class TestBirthdayEmail:
    def test_send_birthday_email(self, mock_email_service):
        from comms.services.email_functions import send_birthday_email

        result = send_birthday_email("parent@test.com", "Sofia")
        assert result is True
        mock_email_service.send_email.assert_called_once()
        call_kwargs = mock_email_service.send_email.call_args
        assert (
            call_kwargs.kwargs["template_name"] == "happy_birthday"
            or call_kwargs[1]["template_name"] == "happy_birthday"
        )


class TestPaymentReminder:
    def test_send_payment_reminder(self, mock_email_service):
        from comms.services.email_functions import send_payment_reminder

        result = send_payment_reminder("parent@test.com", "Pablo", "54.00", "2026-05-01")
        assert result is True
        mock_email_service.send_email.assert_called_once()


class TestMonthlyReport:
    def test_send_monthly_report(self, mock_email_service):
        from comms.services.email_functions import send_monthly_report

        result = send_monthly_report("admin@test.com", {"total_students": 100})
        assert result is True
        mock_email_service.send_email.assert_called_once()


class TestWelcomeEmail:
    def test_send_welcome_email(self, mock_email_service):
        from comms.services.email_functions import send_welcome_email

        result = send_welcome_email(
            parent_email="parent@test.com",
            parent_name="Maria",
            student_name="Lucia",
            group_name="Starters A",
            enrollment_type="Mensual",
            schedule_type="2 dias/semana",
            start_date="15/09/2026",
        )
        assert result is True
        call_kwargs = mock_email_service.send_email.call_args
        # Welcome email uses fail_silently=True
        assert call_kwargs.kwargs.get("fail_silently") is True or call_kwargs[1].get("fail_silently") is True


class TestEnrollmentConfirmation:
    def test_send_enrollment_confirmation(self, mock_email_service):
        from comms.services.email_functions import send_enrollment_confirmation_email

        result = send_enrollment_confirmation_email(
            parent_email="parent@test.com",
            student_name="Daniel",
            gender="m",
            academic_year="2025-2026",
            month="septiembre",
        )
        assert result is True
        mock_email_service.send_email.assert_called_once()


class TestFunFridayEmail:
    def test_send_fun_friday_email(self, mock_email_service):
        from comms.services.email_functions import send_fun_friday_email

        result = send_fun_friday_email(
            recipients=["parent1@test.com", "parent2@test.com"],
            day_name="viernes",
            day_number="17",
            month="abril",
            start_time="15:00",
            end_time="16:30",
            activity_description="Arts and crafts",
            minimum_age=3,
            maximum_age=12,
        )
        assert result is True
        mock_email_service.send_email.assert_called_once()

    def test_send_fun_friday_email_without_image(self, mock_email_service):
        from comms.services.email_functions import send_fun_friday_email

        result = send_fun_friday_email(
            recipients=["parent@test.com"],
            day_name="viernes",
            day_number="17",
            month="abril",
            start_time="15:00",
            end_time="16:30",
            activity_description="Movie day",
            minimum_age=3,
            maximum_age=12,
            event_image_path=None,
        )
        assert result is True


class TestVacationClosure:
    def test_send_vacation_closure_email(self, mock_email_service):
        from comms.services.email_functions import send_vacation_closure_email

        result = send_vacation_closure_email(
            recipients=["parent@test.com"],
            start_closure_day_name="lunes",
            start_closure_day_number="22",
            end_closure_day_name="viernes",
            end_closure_day_number="2",
            month_closure="diciembre",
            closure_reason="Navidad",
            reopening_day_name="lunes",
            reopening_day_number="7",
            month_reopening="enero",
        )
        assert result is True
        mock_email_service.send_email.assert_called_once()


class TestPaymentReminderFull:
    def test_send_payment_reminder_email(self, mock_email_service):
        from comms.services.email_functions import send_payment_reminder_email

        result = send_payment_reminder_email(
            recipients=["parent@test.com"],
            payment_start_day_name="lunes",
            payment_start_day_number="1",
            payment_end_day_name="viernes",
            payment_end_day_number="5",
            month="mayo",
            iban_number="ES1234567890",
            reduced_price_cheque_idioma="34.00",
            telephone_number_bizum="600100001",
        )
        assert result is True


class TestQuarterlyReceipt:
    def test_send_quarterly_receipt_email(self, mock_email_service):
        from comms.services.email_functions import send_quarterly_receipt_email

        result = send_quarterly_receipt_email(
            parent_email="parent@test.com",
            student_name="Hugo",
            month_1="octubre",
            month_2="noviembre",
            month_3="diciembre",
        )
        assert result is True
