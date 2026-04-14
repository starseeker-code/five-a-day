"""Tests for core.middleware — auth middleware edge cases."""

import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def auth_client(client):
    """Client with session authentication set."""
    session = client.session
    session["is_authenticated"] = True
    session["username"] = "testuser"
    session.save()
    client.cookies[client.session.session_key] = session.session_key
    return client


class TestPublicPaths:
    """Verify that public URLs are accessible without authentication."""

    def test_static_not_redirected(self, client):
        # Static files are served by WhiteNoise, but the middleware should not redirect them
        response = client.get("/static/nonexistent.css")
        assert response.status_code != 302

    def test_health_check_public(self, client):
        response = client.get("/health/")
        assert response.status_code == 200

    def test_login_page_public(self, client):
        response = client.get("/login/")
        assert response.status_code == 200

    def test_google_oauth_prefix_public(self, client):
        # The middleware allows any path starting with /auth/google/
        response = client.get("/auth/google/")
        # May return 302 (redirect to Google) or 500 (no credentials), but NOT a login redirect
        assert response.status_code != 302 or "/login/" not in response.get("Location", "")


class TestProtectedPaths:
    """Verify that unauthenticated requests are redirected to login."""

    def test_home_redirects_to_login(self, client):
        response = client.get("/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_students_redirects_to_login(self, client):
        response = client.get("/students/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]

    def test_api_endpoint_redirects_to_login(self, client):
        response = client.get("/api/history/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]


class TestAuthenticatedAccess:
    """Verify that authenticated requests pass through the middleware."""

    def test_authenticated_home_loads(self, authenticated_client):
        response = authenticated_client.get("/")
        assert response.status_code == 200

    def test_session_without_auth_flag_redirects(self, client):
        # Session exists but is_authenticated is not set
        session = client.session
        session["username"] = "someone"
        session.save()
        response = client.get("/")
        assert response.status_code == 302
        assert "/login/" in response["Location"]
