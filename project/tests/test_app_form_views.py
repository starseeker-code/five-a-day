"""Tests for core.views.app_forms — email form GET pages and POST preview/send."""

from datetime import date, timedelta

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestFunFridayForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("fun_friday_form"))
        assert response.status_code == 200
        assert "next_friday" in response.context
        assert "email_html" in response.context

    def test_preview_returns_html(self, authenticated_client):
        next_friday = date.today() + timedelta(days=(4 - date.today().weekday()) % 7 or 7)
        response = authenticated_client.post(
            reverse("fun_friday_form"),
            {
                "action": "preview",
                "event_date": next_friday.isoformat(),
                "start_time": "17:00",
                "end_time": "18:30",
                "activity_description": "<b>Test</b>",
                "min_age": "5",
                "max_age": "12",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "html" in data

    def test_send_all_missing_fields_shows_error(self, authenticated_client):
        response = authenticated_client.post(
            reverse("fun_friday_form"),
            {"event_date": "", "start_time": "", "end_time": ""},
        )
        assert response.status_code == 200  # re-renders form

    def test_send_all_to_parents(self, authenticated_client, student_with_parent):
        next_friday = date.today() + timedelta(days=(4 - date.today().weekday()) % 7 or 7)
        response = authenticated_client.post(
            reverse("fun_friday_form"),
            {
                "event_date": next_friday.isoformat(),
                "start_time": "17:00",
                "end_time": "18:30",
                "activity_description": "<b>Crafts</b>",
                "min_age": "5",
                "max_age": "12",
                "meeting_point": "Main entrance",
            },
        )
        assert response.status_code == 302  # redirects to home


class TestPaymentReminderForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("payment_reminder_form"))
        assert response.status_code == 200
        assert "email_html" in response.context

    def test_preview_returns_html(self, authenticated_client):
        response = authenticated_client.post(
            reverse("payment_reminder_form"),
            {
                "action": "preview",
                "payment_start_date": "2026-04-01",
                "payment_end_date": "2026-04-05",
                "month": "abril",
                "iban_number": "ES1234",
                "telephone_number_bizum": "600000000",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "html" in data

    def test_send_missing_fields_shows_error(self, authenticated_client):
        response = authenticated_client.post(
            reverse("payment_reminder_form"),
            {"payment_start_date": "2026-04-01"},
        )
        assert response.status_code == 200

    def test_send_to_parents(self, authenticated_client, student_with_parent):
        response = authenticated_client.post(
            reverse("payment_reminder_form"),
            {
                "payment_start_date": "2026-04-01",
                "payment_end_date": "2026-04-05",
                "month": "abril",
                "iban_number": "ES1234567890",
                "telephone_number_bizum": "600000000",
                "reduced_price_cheque_idioma": "34€",
            },
        )
        assert response.status_code == 302


class TestVacationClosureForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("vacation_closure_form"))
        assert response.status_code == 200
        assert "email_html" in response.context

    def test_preview_returns_html(self, authenticated_client):
        response = authenticated_client.post(
            reverse("vacation_closure_form"),
            {
                "action": "preview",
                "closure_start_date": "2026-12-23",
                "closure_end_date": "2027-01-03",
                "reopening_date": "2027-01-08",
                "closure_reason": "Navidad",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "html" in data

    def test_send_missing_fields_shows_error(self, authenticated_client):
        response = authenticated_client.post(
            reverse("vacation_closure_form"),
            {"closure_start_date": "2026-12-23"},
        )
        assert response.status_code == 200

    def test_send_to_parents(self, authenticated_client, student_with_parent):
        response = authenticated_client.post(
            reverse("vacation_closure_form"),
            {
                "closure_start_date": "2026-12-23",
                "closure_end_date": "2027-01-03",
                "reopening_date": "2027-01-08",
                "closure_reason": "Navidad",
            },
        )
        assert response.status_code == 302


class TestTaxCertificateForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("tax_certificate_form"))
        assert response.status_code == 200

    def test_preview_returns_html(self, authenticated_client):
        response = authenticated_client.post(
            reverse("tax_certificate_form"),
            {"action": "preview", "year": "2025"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "html" in data

    def test_send_certificates(self, authenticated_client, completed_payment):
        response = authenticated_client.post(
            reverse("tax_certificate_form"),
            {"year": "2025"},
        )
        assert response.status_code == 302


class TestMonthlyReportForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("monthly_report_form"))
        assert response.status_code == 200

    def test_preview_returns_html(self, authenticated_client):
        response = authenticated_client.post(
            reverse("monthly_report_form"),
            {"action": "preview"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "html" in data


class TestReceiptsForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("receipts_form"))
        assert response.status_code == 200


class TestBirthdayForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("birthday_form"))
        assert response.status_code == 200


class TestEnrollmentForm:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("enrollment_form"))
        assert response.status_code == 200


class TestTestSendNoEnvVars:
    """Test that test_send fails gracefully without EMAIL_TEST_* env vars."""

    def test_fun_friday_test_send_no_env(self, authenticated_client, monkeypatch):
        monkeypatch.delenv("EMAIL_TEST_1", raising=False)
        monkeypatch.delenv("EMAIL_TEST_2", raising=False)
        next_friday = date.today() + timedelta(days=(4 - date.today().weekday()) % 7 or 7)
        response = authenticated_client.post(
            reverse("fun_friday_form"),
            {
                "action": "test_send",
                "event_date": next_friday.isoformat(),
                "start_time": "17:00",
                "end_time": "18:30",
                "activity_description": "Test",
                "min_age": "5",
                "max_age": "12",
            },
        )
        data = response.json()
        assert data["success"] is False

    def test_payment_reminder_test_send_no_env(self, authenticated_client, monkeypatch):
        monkeypatch.delenv("EMAIL_TEST_1", raising=False)
        monkeypatch.delenv("EMAIL_TEST_2", raising=False)
        response = authenticated_client.post(
            reverse("payment_reminder_form"),
            {
                "action": "test_send",
                "payment_start_date": "2026-04-01",
                "payment_end_date": "2026-04-05",
                "month": "abril",
                "iban_number": "ES1234",
                "telephone_number_bizum": "600000000",
            },
        )
        data = response.json()
        assert data["success"] is False

    def test_vacation_closure_test_send_no_env(self, authenticated_client, monkeypatch):
        monkeypatch.delenv("EMAIL_TEST_1", raising=False)
        monkeypatch.delenv("EMAIL_TEST_2", raising=False)
        response = authenticated_client.post(
            reverse("vacation_closure_form"),
            {
                "action": "test_send",
                "closure_start_date": "2026-12-23",
                "closure_end_date": "2027-01-03",
                "reopening_date": "2027-01-08",
                "closure_reason": "Navidad",
            },
        )
        data = response.json()
        assert data["success"] is False

    def test_tax_certificate_test_send_no_env(self, authenticated_client, monkeypatch):
        monkeypatch.delenv("EMAIL_TEST_1", raising=False)
        monkeypatch.delenv("EMAIL_TEST_2", raising=False)
        response = authenticated_client.post(
            reverse("tax_certificate_form"),
            {"action": "test_send", "year": "2025"},
        )
        data = response.json()
        assert data["success"] is False
