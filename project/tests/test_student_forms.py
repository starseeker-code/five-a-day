"""Tests for students.forms — StudentForm and ParentForm validation."""

from datetime import date, timedelta

import pytest

from students.forms import ParentForm, StudentForm

pytestmark = pytest.mark.django_db


class TestStudentForm:
    def test_valid_form(self, group):
        form = StudentForm(
            data={
                "first_name": "Test",
                "last_name": "Student",
                "birth_date": "2018-05-15",
                "school": "CEIP Test",
                "gdpr_signed": True,
                "group": group.id,
            }
        )
        assert form.is_valid()

    def test_future_birth_date_rejected(self, group):
        future = (date.today() + timedelta(days=1)).isoformat()
        form = StudentForm(
            data={
                "first_name": "Test",
                "last_name": "Student",
                "birth_date": future,
                "group": group.id,
            }
        )
        assert not form.is_valid()
        assert "birth_date" in form.errors

    def test_spanish_date_format(self, group):
        form = StudentForm(
            data={
                "first_name": "Test",
                "last_name": "Student",
                "birth_date": "15/05/2018",
                "group": group.id,
            }
        )
        assert form.is_valid()

    def test_missing_required_fields(self):
        form = StudentForm(data={})
        assert not form.is_valid()
        assert "first_name" in form.errors
        assert "last_name" in form.errors


class TestParentForm:
    def test_valid_form(self):
        form = ParentForm(
            data={
                "first_name": "María",
                "last_name": "García",
                "dni": "12345678A",
                "phone": "600111222",
                "email": "maria@test.com",
            }
        )
        assert form.is_valid()

    def test_short_dni_rejected(self):
        form = ParentForm(
            data={
                "first_name": "María",
                "last_name": "García",
                "dni": "123",
                "phone": "600111222",
                "email": "maria@test.com",
            }
        )
        assert not form.is_valid()
        assert "dni" in form.errors

    def test_dni_uppercased(self):
        form = ParentForm(
            data={
                "first_name": "María",
                "last_name": "García",
                "dni": "12345678a",
                "phone": "600111222",
                "email": "maria@test.com",
            }
        )
        assert form.is_valid()
        assert form.cleaned_data["dni"] == "12345678A"
