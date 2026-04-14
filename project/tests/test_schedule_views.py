"""Tests for core.views.schedule — schedule, save_schedule_slot, fun_friday."""

import json

import pytest
from django.urls import reverse

from core.models import ScheduleSlot

pytestmark = pytest.mark.django_db


class TestScheduleView:
    def test_loads_ok(self, authenticated_client, group):
        response = authenticated_client.get(reverse("schedule_view"))
        assert response.status_code == 200
        assert "groups_json" in response.context

    def test_groups_in_context(self, authenticated_client, group):
        response = authenticated_client.get(reverse("schedule_view"))
        groups = json.loads(response.context["groups_json"])
        assert len(groups) == 1
        assert groups[0]["name"] == "Group A"

    def test_slots_in_context(self, authenticated_client, group):
        ScheduleSlot.objects.create(row=0, day=0, col=0, group=group)
        response = authenticated_client.get(reverse("schedule_view"))
        slots = json.loads(response.context["slots_json"])
        assert len(slots) == 1
        assert slots[0]["group_id"] == group.id


class TestSaveScheduleSlot:
    def test_assign_group_to_slot(self, authenticated_client, group):
        response = authenticated_client.post(
            reverse("save_schedule_slot"),
            data=json.dumps({"row": 0, "day": 1, "col": 0, "group_id": group.id}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert ScheduleSlot.objects.filter(row=0, day=1, col=0, group=group).exists()

    def test_clear_slot(self, authenticated_client, group):
        ScheduleSlot.objects.create(row=0, day=2, col=0, group=group)
        response = authenticated_client.post(
            reverse("save_schedule_slot"),
            data=json.dumps({"row": 0, "day": 2, "col": 0, "group_id": None}),
            content_type="application/json",
        )
        assert response.status_code == 200
        assert not ScheduleSlot.objects.filter(row=0, day=2, col=0).exists()

    def test_rejects_get(self, authenticated_client):
        response = authenticated_client.get(reverse("save_schedule_slot"))
        assert response.status_code == 405


class TestFunFridayView:
    def test_loads_ok(self, authenticated_client, student):
        response = authenticated_client.get(reverse("fun_friday_view"))
        assert response.status_code == 200
        assert "students" in response.context
        assert "this_friday" in response.context

    def test_excludes_adult_students(self, authenticated_client, student, adult_student):
        response = authenticated_client.get(reverse("fun_friday_view"))
        student_ids = {s.id for s in response.context["students"]}
        assert student.id in student_ids
        assert adult_student.id not in student_ids
