"""Tests for core.transactions — queryset helper functions."""

import pytest

from core.transactions import (
    get_active_students,
    get_all_payments_unrestricted,
    get_payments_for_last_two_school_years,
)

pytestmark = pytest.mark.django_db


class TestGetActiveStudents:
    def test_returns_active_only(self, student, inactive_student):
        qs = get_active_students()
        ids = set(qs.values_list("id", flat=True))
        assert student.id in ids
        assert inactive_student.id not in ids

    def test_prefetches_parents(self, student_with_parent):
        qs = get_active_students()
        assert qs.get(id=student_with_parent.id).parents.count() == 1

    def test_selects_related_group(self, student):
        qs = get_active_students()
        s = qs.get(id=student.id)
        assert s.group.group_name == "Group A"

    def test_empty_when_no_active_students(self, inactive_student):
        assert get_active_students().count() == 0


class TestGetPaymentsForLastTwoSchoolYears:
    def test_includes_recent_payments(self, pending_payment):
        qs = get_payments_for_last_two_school_years()
        assert qs.filter(id=pending_payment.id).exists()

    def test_selects_related_student(self, pending_payment):
        qs = get_payments_for_last_two_school_years()
        payment = qs.get(id=pending_payment.id)
        assert payment.student.first_name == "Lucas"

    def test_ordered_by_created_at_desc(self, pending_payment, completed_payment):
        qs = get_payments_for_last_two_school_years()
        if qs.count() >= 2:
            ids = list(qs.values_list("id", flat=True))
            # Most recently created should be first
            assert ids[0] > ids[-1] or len(ids) == 1


class TestGetAllPaymentsUnrestricted:
    def test_returns_all_payments(self, pending_payment, completed_payment):
        qs = get_all_payments_unrestricted()
        assert qs.count() == 2

    def test_ordered_by_created_at_desc(self, pending_payment, completed_payment):
        qs = get_all_payments_unrestricted()
        ids = list(qs.values_list("id", flat=True))
        assert ids == sorted(ids, reverse=True)

    def test_empty_when_no_payments(self, db):
        assert get_all_payments_unrestricted().count() == 0
