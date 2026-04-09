"""Tests for views — HTTP endpoints, auth, AJAX APIs."""
import pytest
import json
from decimal import Decimal
from datetime import date

from django.urls import reverse

from students.models import Student, Parent, Teacher, Group
from billing.models import Payment, Enrollment, SiteConfiguration
from core.models import TodoItem, HistoryLog

# All view tests need DB access
pytestmark = pytest.mark.django_db


# ── Authentication / Middleware ───────────────────────────────────────────────


class TestAuthMiddleware:
    def test_unauthenticated_redirects_to_login(self, client):
        response = client.get(reverse("home"))
        assert response.status_code == 302
        assert "/login/" in response.url

    def test_login_page_accessible(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_health_check_public(self, client):
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_login_with_valid_credentials(self, client, settings):
        import os
        os.environ["LOGIN_USERNAME"] = "testuser"
        os.environ["LOGIN_PASSWORD"] = "testpass"
        response = client.post(
            reverse("login"),
            {"username": "testuser", "password": "testpass"},
        )
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_login_with_invalid_credentials(self, client):
        response = client.post(
            reverse("login"),
            {"username": "wrong", "password": "wrong"},
        )
        assert response.status_code == 200  # Re-renders login page

    def test_logout(self, authenticated_client):
        response = authenticated_client.get(reverse("logout"))
        assert response.status_code == 302
        # After logout, accessing home should redirect to login
        response = authenticated_client.get(reverse("home"))
        assert response.status_code == 302


# ── Dashboard ────────────────────────────────────────────────────────────────


class TestDashboard:
    def test_home_page_loads(self, authenticated_client):
        response = authenticated_client.get(reverse("home"))
        assert response.status_code == 200

    def test_all_info_loads(self, authenticated_client):
        response = authenticated_client.get(reverse("all_info"))
        assert response.status_code == 200


# ── Student Views ────────────────────────────────────────────────────────────


class TestStudentViews:
    def test_students_list(self, authenticated_client, student_with_parent, active_enrollment):
        response = authenticated_client.get(reverse("students_list"))
        assert response.status_code == 200

    def test_student_detail(self, authenticated_client, student):
        response = authenticated_client.get(
            reverse("student_detail", kwargs={"student_id": student.id})
        )
        assert response.status_code == 200

    def test_student_create_page(self, authenticated_client, group):
        response = authenticated_client.get(reverse("student_create"))
        assert response.status_code == 200

    def test_search_students_api(self, authenticated_client, student):
        response = authenticated_client.get(
            reverse("search_students") + "?q=Lucas"
        )
        assert response.status_code == 200


# ── Parent Views ─────────────────────────────────────────────────────────────


class TestParentViews:
    def test_parent_create_page(self, authenticated_client):
        response = authenticated_client.get(reverse("parent_create"))
        assert response.status_code == 200

    def test_search_parents_api(self, authenticated_client, parent):
        response = authenticated_client.get(
            reverse("search_parents") + "?q=María"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) >= 1


# ── Payment Views ────────────────────────────────────────────────────────────


class TestPaymentViews:
    def test_payments_list(self, authenticated_client):
        response = authenticated_client.get(reverse("payments_list"))
        assert response.status_code == 200

    def test_payment_create_page(self, authenticated_client):
        response = authenticated_client.get(reverse("create_payment"))
        assert response.status_code == 200

    def test_payment_detail(self, authenticated_client, pending_payment):
        response = authenticated_client.get(
            reverse("payment_detail_view", kwargs={"payment_id": pending_payment.id})
        )
        assert response.status_code == 200

    def test_quick_complete_payment(self, authenticated_client, pending_payment):
        response = authenticated_client.post(
            reverse("quick_complete_payment", kwargs={"payment_id": pending_payment.id}),
            data=json.dumps({"payment_method": "cash"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        pending_payment.refresh_from_db()
        assert pending_payment.payment_status == "completed"

    def test_quick_complete_invalid_method(self, authenticated_client, pending_payment):
        response = authenticated_client.post(
            reverse("quick_complete_payment", kwargs={"payment_id": pending_payment.id}),
            data=json.dumps({"payment_method": "bitcoin"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_payment_statistics(self, authenticated_client):
        response = authenticated_client.get(reverse("payment_statistics"))
        assert response.status_code == 200
        data = response.json()
        assert "total_payments" in data

    def test_export_payments_csv(self, authenticated_client, completed_payment):
        response = authenticated_client.get(reverse("export_payments"))
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_validate_student_parent_valid(
        self, authenticated_client, student_with_parent, parent
    ):
        response = authenticated_client.post(
            reverse("validate_student_parent"),
            data=json.dumps({
                "student_id": student_with_parent.id,
                "parent_id": parent.id,
            }),
            content_type="application/json",
        )
        data = response.json()
        assert data["valid"] is True

    def test_validate_student_parent_invalid(
        self, authenticated_client, student, second_parent
    ):
        response = authenticated_client.post(
            reverse("validate_student_parent"),
            data=json.dumps({
                "student_id": student.id,
                "parent_id": second_parent.id,
            }),
            content_type="application/json",
        )
        data = response.json()
        assert data["valid"] is False


# ── Todo API ─────────────────────────────────────────────────────────────────


class TestTodoAPI:
    def test_create_todo(self, authenticated_client):
        response = authenticated_client.post(
            reverse("create_todo"),
            data=json.dumps({"text": "Test task", "due_date": "2025-10-15"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["todo"]["text"] == "Test task"
        assert TodoItem.objects.filter(text="Test task").exists()

    def test_create_todo_empty_text(self, authenticated_client):
        response = authenticated_client.post(
            reverse("create_todo"),
            data=json.dumps({"text": "", "due_date": "2025-10-15"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_complete_todo(self, authenticated_client, db):
        todo = TodoItem.objects.create(text="To complete", due_date=date(2025, 10, 15))
        response = authenticated_client.post(
            reverse("complete_todo", kwargs={"todo_id": todo.id})
        )
        assert response.status_code == 200
        assert not TodoItem.objects.filter(id=todo.id).exists()
        assert HistoryLog.objects.filter(action="todo_completed").exists()


# ── History API ──────────────────────────────────────────────────────────────


class TestHistoryAPI:
    def test_history_list(self, authenticated_client, db):
        HistoryLog.log("payment_completed", "Test entry")
        response = authenticated_client.get(reverse("history_list"))
        assert response.status_code == 200
        data = response.json()
        assert len(data["entries"]) >= 1

    def test_history_list_pagination(self, authenticated_client, db):
        for i in range(25):
            HistoryLog.log("payment_completed", f"Entry {i}")
        response = authenticated_client.get(reverse("history_list") + "?offset=0")
        data = response.json()
        assert len(data["entries"]) == 20
        assert data["has_more"] is True

        response = authenticated_client.get(reverse("history_list") + "?offset=20")
        data = response.json()
        assert len(data["entries"]) == 5
        assert data["has_more"] is False


# ── Management Views ─────────────────────────────────────────────────────────


class TestManagementViews:
    def test_management_page(self, authenticated_client, site_config, teacher, group):
        response = authenticated_client.get(reverse("management"))
        assert response.status_code == 200

    def test_update_site_config(self, authenticated_client, site_config):
        response = authenticated_client.post(
            reverse("update_site_config"),
            data=json.dumps({"full_time_monthly_fee": "58.00"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        site_config.refresh_from_db()
        assert site_config.full_time_monthly_fee == Decimal("58.00")

    def test_create_teacher(self, authenticated_client, db):
        response = authenticated_client.post(
            reverse("create_teacher"),
            data=json.dumps({
                "first_name": "John",
                "last_name": "Smith",
                "email": "john@fiveaday.test",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert Teacher.objects.filter(email="john@fiveaday.test").exists()

    def test_create_teacher_duplicate_email(self, authenticated_client, teacher):
        response = authenticated_client.post(
            reverse("create_teacher"),
            data=json.dumps({
                "first_name": "Duplicate",
                "last_name": "Teacher",
                "email": teacher.email,
            }),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_group(self, authenticated_client, teacher):
        response = authenticated_client.post(
            reverse("create_group"),
            data=json.dumps({
                "group_name": "Group B",
                "teacher_id": teacher.id,
                "color": "#ef4444",
            }),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert Group.objects.filter(group_name="Group B").exists()

    def test_api_get_teachers(self, authenticated_client, teacher):
        response = authenticated_client.get(reverse("api_get_teachers"))
        assert response.status_code == 200
        data = response.json()
        assert len(data["teachers"]) >= 1


# ── Schedule Views ───────────────────────────────────────────────────────────


class TestScheduleViews:
    def test_schedule_page(self, authenticated_client, group):
        response = authenticated_client.get(reverse("schedule_view"))
        assert response.status_code == 200

    def test_fun_friday_page(self, authenticated_client, student):
        response = authenticated_client.get(reverse("fun_friday_view"))
        assert response.status_code == 200


# ── App Form Views ───────────────────────────────────────────────────────────


class TestAppFormViews:
    def test_apps_page(self, authenticated_client):
        response = authenticated_client.get(reverse("apps"))
        assert response.status_code == 200

    @pytest.mark.parametrize("url_name", [
        "fun_friday_form",
        "payment_reminder_form",
        "vacation_closure_form",
        "tax_certificate_form",
        "monthly_report_form",
        "birthday_form",
        "receipts_form",
        "enrollment_form",
    ])
    def test_app_form_pages_load(self, authenticated_client, url_name):
        response = authenticated_client.get(reverse(url_name))
        assert response.status_code == 200

    def test_welcome_form_redirects(self, authenticated_client):
        response = authenticated_client.get(reverse("welcome_form"))
        assert response.status_code == 302


# ── Enrollment API ───────────────────────────────────────────────────────────


class TestEnrollmentAPI:
    def test_update_modality(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.post(
            reverse("update_enrollment_modality", kwargs={"student_id": student.id}),
            data=json.dumps({"payment_modality": "quarterly"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        active_enrollment.refresh_from_db()
        assert active_enrollment.payment_modality == "quarterly"

    def test_update_modality_invalid(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.post(
            reverse("update_enrollment_modality", kwargs={"student_id": student.id}),
            data=json.dumps({"payment_modality": "weekly"}),
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_language_cheque_students(self, authenticated_client, active_enrollment):
        active_enrollment.has_language_cheque = True
        active_enrollment.save()
        response = authenticated_client.get(reverse("language_cheque_students"))
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1


# ── Error Pages ──────────────────────────────────────────────────────────────


class TestErrorPages:
    @pytest.mark.parametrize("url_name,status", [
        ("test_error_400", 400),
        ("test_error_403", 403),
        ("test_error_404", 404),
        ("test_error_405", 405),
        ("test_error_500", 500),
    ])
    def test_error_pages_render(self, authenticated_client, url_name, status):
        response = authenticated_client.get(reverse(url_name))
        assert response.status_code == status
