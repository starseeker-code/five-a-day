"""Tests for core.views.auth — login, logout, OAuth redirect."""

import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


class TestLoginView:
    def test_get_renders_login_page(self, client):
        response = client.get(reverse("login"))
        assert response.status_code == 200

    def test_authenticated_user_redirects_to_home(self, authenticated_client):
        response = authenticated_client.get(reverse("login"))
        assert response.status_code == 302
        assert response.url == reverse("home")

    def test_valid_credentials_authenticates(self, client, monkeypatch):
        monkeypatch.setenv("LOGIN_USERNAME", "admin")
        monkeypatch.setenv("LOGIN_PASSWORD", "secret")
        response = client.post(reverse("login"), {"username": "admin", "password": "secret"})
        assert response.status_code == 302
        assert response.url == reverse("home")
        assert client.session["is_authenticated"] is True

    def test_invalid_credentials_rejected(self, client, monkeypatch):
        monkeypatch.setenv("LOGIN_USERNAME", "admin")
        monkeypatch.setenv("LOGIN_PASSWORD", "secret")
        response = client.post(reverse("login"), {"username": "admin", "password": "wrong"})
        assert response.status_code == 200
        assert not client.session.get("is_authenticated")

    def test_missing_env_vars_shows_error(self, client, monkeypatch):
        monkeypatch.delenv("LOGIN_USERNAME", raising=False)
        monkeypatch.delenv("LOGIN_PASSWORD", raising=False)
        response = client.post(reverse("login"), {"username": "x", "password": "y"})
        assert response.status_code == 200
        assert not client.session.get("is_authenticated")


class TestLogoutView:
    def test_logout_clears_session(self, authenticated_client):
        response = authenticated_client.get(reverse("logout"))
        assert response.status_code == 302
        assert response.url == reverse("login")
        assert not authenticated_client.session.get("is_authenticated")


class TestGoogleOAuthRedirect:
    def test_no_credentials_redirects_to_login(self, authenticated_client, monkeypatch):
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("GOOGLE_CLIENT_SECRET", raising=False)
        response = authenticated_client.get(reverse("google_oauth_redirect"))
        assert response.status_code == 302
        assert response.url == reverse("login")
