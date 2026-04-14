"""Tests for core.views.parents — ParentCreateView."""

import pytest
from django.urls import reverse

from students.models import Parent

pytestmark = pytest.mark.django_db


class TestParentCreateView:
    def test_get_renders_form(self, authenticated_client):
        response = authenticated_client.get(reverse("parent_create"))
        assert response.status_code == 200

    def test_post_creates_parent(self, authenticated_client):
        response = authenticated_client.post(
            reverse("parent_create"),
            {
                "first_name": "Laura",
                "last_name": "Fernández",
                "dni": "11223344X",
                "phone": "600111222",
                "email": "laura@test.com",
                "iban": "ES0011223344556677889900",
            },
        )
        assert response.status_code == 302
        assert Parent.objects.filter(dni="11223344X").exists()
        parent = Parent.objects.get(dni="11223344X")
        assert f"parent_id={parent.id}" in response.url

    def test_post_existing_dni_shows_form_error(self, authenticated_client, parent):
        """Duplicate DNI is caught by ModelForm unique validation."""
        response = authenticated_client.post(
            reverse("parent_create"),
            {
                "first_name": "Different",
                "last_name": "Name",
                "dni": parent.dni,  # same DNI as existing parent
                "phone": "600999888",
                "email": "different@test.com",
            },
        )
        assert response.status_code == 200  # re-renders form with uniqueness error

    def test_post_invalid_data_shows_form(self, authenticated_client):
        response = authenticated_client.post(
            reverse("parent_create"),
            {"first_name": "", "last_name": "", "dni": ""},
        )
        assert response.status_code == 200  # re-renders form with errors
