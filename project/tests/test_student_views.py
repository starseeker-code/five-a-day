"""Tests for core.views.students — list, detail, create, update, search."""

import pytest
from django.urls import reverse

from students.models import Student

pytestmark = pytest.mark.django_db


class TestStudentListView:
    def test_loads_ok(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.get(reverse("students_list"))
        assert response.status_code == 200

    def test_excludes_inactive_students(self, authenticated_client, inactive_student):
        response = authenticated_client.get(reverse("students_list"))
        student_ids = {s.id for s in response.context["students"]}
        assert inactive_student.id not in student_ids

    def test_search_by_name(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.get(reverse("students_list"), {"search": "Lucas"})
        assert response.status_code == 200
        student_ids = {s.id for s in response.context["students"]}
        assert student.id in student_ids

    def test_search_no_results(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.get(reverse("students_list"), {"search": "nonexistent"})
        assert response.status_code == 200
        assert len(response.context["students"]) == 0

    def test_context_has_groups_and_parents(self, authenticated_client, student, active_enrollment):
        response = authenticated_client.get(reverse("students_list"))
        assert "groups" in response.context
        assert "parents" in response.context


class TestStudentDetailView:
    def test_loads_ok(self, authenticated_client, student):
        response = authenticated_client.get(reverse("student_detail", args=[student.id]))
        assert response.status_code == 200
        assert response.context["student"] == student

    def test_shows_parents(self, authenticated_client, student_with_parent):
        response = authenticated_client.get(reverse("student_detail", args=[student_with_parent.id]))
        assert len(response.context["parents"]) == 1

    def test_nonexistent_student_404(self, authenticated_client):
        response = authenticated_client.get(reverse("student_detail", args=[99999]))
        assert response.status_code == 404


class TestStudentCreateView:
    def test_get_renders_form(self, authenticated_client, group, site_config, enrollment_type_monthly):
        response = authenticated_client.get(reverse("student_create"))
        assert response.status_code == 200
        assert "enrollment_form" in response.context

    def test_success_page(self, authenticated_client, group, site_config, enrollment_type_monthly):
        url = reverse("student_create") + "?success=1&student_name=Test&fee=40"
        response = authenticated_client.get(url)
        assert response.status_code == 200
        assert response.context["show_success"] is True

    def test_adult_mode_context(self, authenticated_client, group, site_config, enrollment_type_monthly):
        response = authenticated_client.get(reverse("student_create") + "?mode=adult")
        assert response.status_code == 200
        assert response.context["is_adult_mode"] is True


class TestStudentCreateViewPost:
    def test_creates_student_with_enrollment(
        self, authenticated_client, parent, group, site_config, enrollment_type_monthly
    ):
        response = authenticated_client.post(
            reverse("student_create") + f"?parent_id={parent.id}",
            {
                "first_name": "Nuevo",
                "last_name": "Alumno",
                "birth_date": "2018-03-10",
                "school": "CEIP Nuevo",
                "gdpr_signed": "on",
                "group": group.id,
                "parent_id": parent.id,
                "enrollment_plan": "monthly_full",
            },
        )
        assert response.status_code == 302
        assert Student.objects.filter(first_name="Nuevo").exists()

    def test_creates_adult_student(self, authenticated_client, group, site_config, enrollment_type_adults):
        response = authenticated_client.post(
            reverse("student_create") + "?mode=adult",
            {
                "first_name": "Adulto",
                "last_name": "Nuevo",
                "birth_date": "1990-01-01",
                "gdpr_signed": "on",
                "group": group.id,
                "is_adult_mode": "true",
                "adult_email": "adulto@test.com",
                "adult_phone": "600111222",
                "enrollment_plan": "monthly_full",
            },
        )
        assert response.status_code == 302
        assert Student.objects.filter(first_name="Adulto").exists()


class TestSearchStudents:
    def test_returns_students_page(self, authenticated_client, student):
        response = authenticated_client.get(reverse("search_students"))
        assert response.status_code == 200
        assert "students" in response.context
