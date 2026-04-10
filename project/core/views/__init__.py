"""
Core views package — re-exports all views for URL routing compatibility.
"""

# Auth
from core.views.auth import (
    login_view, logout_view, google_oauth_redirect, google_oauth_callback,
)

# Dashboard
from core.views.dashboard import home, all_info

# Errors & health
from core.views.errors import (
    handler400, handler403, handler404, handler405, handler500,
    test_error_400, test_error_403, test_error_404, test_error_405, test_error_500,
    health_check,
)

# Students
from core.views.students import (
    StudentCreateView, StudentListView, StudentUpdateView,
    StudentDetailView, search_students, handle_student_form, student_detail,
    update_student, get_next_friday, get_last_friday, get_ff_student_ids,
)

# Parents
from core.views.parents import ParentCreateView

# Payments
from core.views.payments import (
    payments_list, create_payment, payment_detail, payment_detail_view,
    update_payment, delete_payment, deactivate_payment, quick_complete_payment,
    get_payment_details, payment_statistics, search_payments, search_parents,
    validate_student_parent, export_payments, export_database_excel,
    parse_date_value,
)

# Fun Friday attendance
from core.views.fun_friday_attendance import (
    toggle_fun_friday_this_week, add_fun_friday_attendance,
    remove_fun_friday_attendance,
)

# Management & enrollment API
from core.views.management import (
    gestion_view, update_site_config, create_teacher, create_group,
    api_get_teachers, update_enrollment_modality, language_cheque_students,
)

# App forms (email tools)
from core.views.app_forms import (
    apps_view, fun_friday_form, payment_reminder_form, vacation_closure_form,
    tax_certificate_form, monthly_report_form, welcome_form, birthday_form,
    receipts_form, enrollment_form,
)

# Schedule
from core.views.schedule import schedule_view, save_schedule_slot, fun_friday_view

# Todos & history
from core.views.todos import create_todo, complete_todo, history_list

# Support
from core.views.support import submit_support_ticket
