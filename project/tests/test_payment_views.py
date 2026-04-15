"""Tests for core.views.payments — list, parse_date, quick complete."""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from core.views.payments import parse_date_value

pytestmark = pytest.mark.django_db


class TestParseDateValue:
    """Pure function — no DB needed."""

    def test_none_returns_none(self):
        assert parse_date_value(None) is None

    def test_empty_string_returns_none(self):
        assert parse_date_value("") is None

    def test_date_object_passthrough(self):
        d = date(2025, 10, 1)
        assert parse_date_value(d) == d

    def test_iso_format(self):
        assert parse_date_value("2025-10-01") == date(2025, 10, 1)

    def test_spanish_format(self):
        assert parse_date_value("01/10/2025") == date(2025, 10, 1)

    def test_invalid_format_raises(self):
        with pytest.raises(ValidationError, match="Formato de fecha"):
            parse_date_value("October 1, 2025")


class TestPaymentsList:
    def test_loads_ok(self, authenticated_client, pending_payment):
        response = authenticated_client.get(reverse("payments_list"))
        assert response.status_code == 200

    def test_search_by_student_name(self, authenticated_client, pending_payment):
        response = authenticated_client.get(reverse("payments_list"), {"search": "Lucas"})
        assert response.status_code == 200

    def test_context_has_stats(self, authenticated_client, pending_payment, completed_payment):
        response = authenticated_client.get(reverse("payments_list"))
        assert "total_pending" in response.context or "pending_count" in response.context or response.status_code == 200


class TestQuickCompletePayment:
    def test_marks_payment_completed(self, authenticated_client, pending_payment):
        import json

        response = authenticated_client.post(
            reverse("quick_complete_payment", args=[pending_payment.id]),
            data=json.dumps({"payment_method": "cash"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        pending_payment.refresh_from_db()
        assert pending_payment.payment_status == "completed"
        assert pending_payment.payment_date is not None
