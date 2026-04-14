"""Tests for core.views.payments — create_payment and update_payment."""

import pytest
from django.urls import reverse

from billing.models import Payment

pytestmark = pytest.mark.django_db


class TestCreatePayment:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("create_payment"))
        assert response.status_code == 200

    def test_post_creates_payment(self, authenticated_client, student_with_parent, parent, active_enrollment):
        response = authenticated_client.post(
            reverse("create_payment"),
            {
                "student_id": student_with_parent.id,
                "parent_id": parent.id,
                "payment_type": "monthly",
                "payment_method": "transfer",
                "amount": "54.00",
                "currency": "EUR",
                "payment_status": "pending",
                "due_date": "2026-05-01",
                "concept": "Test payment",
            },
        )
        assert response.status_code == 302
        assert Payment.objects.filter(concept="Test payment").exists()

    def test_post_invalid_parent_relationship(self, authenticated_client, student, second_parent, active_enrollment):
        """Parent not linked to student should be rejected."""
        response = authenticated_client.post(
            reverse("create_payment"),
            {
                "student_id": student.id,
                "parent_id": second_parent.id,
                "payment_type": "monthly",
                "payment_method": "cash",
                "amount": "54.00",
                "due_date": "2026-05-01",
                "concept": "Invalid",
            },
        )
        assert response.status_code == 302  # redirects with error


class TestPaymentDetailView:
    def test_renders_payment(self, authenticated_client, pending_payment):
        response = authenticated_client.get(
            reverse("payment_detail_view", args=[pending_payment.id]),
        )
        assert response.status_code == 200
        assert response.context["payment"] == pending_payment

    def test_nonexistent_payment_404(self, authenticated_client):
        response = authenticated_client.get(reverse("payment_detail_view", args=[99999]))
        assert response.status_code == 404


class TestUpdatePayment:
    def test_updates_payment(self, authenticated_client, student_with_parent, pending_payment):
        import json

        response = authenticated_client.post(
            reverse("update_payment", args=[pending_payment.id]),
            data=json.dumps({"amount": "60.00", "concept": "Updated"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        pending_payment.refresh_from_db()
        assert pending_payment.concept == "Updated"


class TestExportDatabaseExcel:
    def test_exports_xlsx(self, authenticated_client, student_with_parent, active_enrollment, pending_payment):
        response = authenticated_client.get(reverse("export_database_excel"))
        assert response.status_code == 200
        assert "spreadsheetml" in response["Content-Type"]
