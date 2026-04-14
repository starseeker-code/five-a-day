"""Tests for core.context_processors — notification context, scheduled apps."""

from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import RequestFactory

from core.context_processors import today_notifications
from core.models import HistoryLog, TodoItem

pytestmark = pytest.mark.django_db


@pytest.fixture
def rf():
    return RequestFactory()


@pytest.fixture
def request_obj(rf):
    return rf.get("/")


class TestTodayNotifications:
    def test_returns_expected_keys(self, request_obj):
        ctx = today_notifications(request_obj)
        assert "notifications_today_todos" in ctx
        assert "notifications_today_apps" in ctx
        assert "notifications_count" in ctx
        assert "history_count" in ctx
        assert "support_email" in ctx

    def test_todos_due_today_included(self, request_obj):
        TodoItem.objects.create(text="Due today", due_date=date.today())
        ctx = today_notifications(request_obj)
        assert len(ctx["notifications_today_todos"]) == 1
        assert ctx["notifications_today_todos"][0]["text"] == "Due today"

    def test_todos_due_other_day_excluded(self, request_obj):
        TodoItem.objects.create(text="Tomorrow", due_date=date.today() + timedelta(days=1))
        ctx = today_notifications(request_obj)
        assert len(ctx["notifications_today_todos"]) == 0

    @patch("core.context_processors.date")
    def test_friday_apps_included_on_friday(self, mock_date, request_obj):
        # 2026-04-17 is a Friday
        mock_date.today.return_value = date(2026, 4, 17)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        ctx = today_notifications(request_obj)
        app_names = [a["name"] for a in ctx["notifications_today_apps"]]
        assert "Fun Friday" in app_names

    @patch("core.context_processors.date")
    def test_friday_apps_excluded_on_monday(self, mock_date, request_obj):
        # 2026-04-13 is a Monday
        mock_date.today.return_value = date(2026, 4, 13)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        ctx = today_notifications(request_obj)
        app_names = [a["name"] for a in ctx["notifications_today_apps"]]
        assert "Fun Friday" not in app_names

    @patch("core.context_processors.date")
    def test_monthly_apps_on_day_1(self, mock_date, request_obj):
        mock_date.today.return_value = date(2026, 5, 1)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        ctx = today_notifications(request_obj)
        app_names = [a["name"] for a in ctx["notifications_today_apps"]]
        assert "Pago Mensual" in app_names

    @patch("core.context_processors.date")
    def test_monthly_apps_excluded_on_day_15(self, mock_date, request_obj):
        mock_date.today.return_value = date(2026, 5, 15)
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)
        ctx = today_notifications(request_obj)
        app_names = [a["name"] for a in ctx["notifications_today_apps"]]
        assert "Pago Mensual" not in app_names

    def test_history_count_matches_db(self, request_obj):
        for i in range(3):
            HistoryLog.log("config_updated", f"Test entry {i}")
        ctx = today_notifications(request_obj)
        assert ctx["history_count"] == 3

    def test_support_email_from_settings(self, request_obj, settings):
        settings.SUPPORT_EMAIL = "test@example.com"
        ctx = today_notifications(request_obj)
        assert ctx["support_email"] == "test@example.com"

    def test_notifications_count_sums_todos_and_apps(self, request_obj):
        TodoItem.objects.create(text="Task 1", due_date=date.today())
        TodoItem.objects.create(text="Task 2", due_date=date.today())
        ctx = today_notifications(request_obj)
        # count = 2 todos + whatever apps match today
        assert ctx["notifications_count"] >= 2

    def test_graceful_on_empty_db(self, request_obj):
        ctx = today_notifications(request_obj)
        assert ctx["notifications_today_todos"] == []
        assert ctx["history_count"] == 0
