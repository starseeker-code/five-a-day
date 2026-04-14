"""
Core views package — re-exports all views for URL routing compatibility.
"""

# Auth
# App forms (email tools)
from core.views.app_forms import (
    apps_view,
    birthday_form,
    enrollment_form,
    fun_friday_form,
    monthly_report_form,
    payment_reminder_form,
    receipts_form,
    tax_certificate_form,
    vacation_closure_form,
    welcome_form,
)
from core.views.auth import (
    google_oauth_callback,
    google_oauth_redirect,
    login_view,
    logout_view,
)

# Dashboard
from core.views.dashboard import all_info, home

# Errors & health
from core.views.errors import (
    handler400,
    handler403,
    handler404,
    handler405,
    handler500,
    health_check,
    test_error_400,
    test_error_403,
    test_error_404,
    test_error_405,
    test_error_500,
)

# Fun Friday attendance
from core.views.fun_friday_attendance import (
    add_fun_friday_attendance,
    remove_fun_friday_attendance,
    toggle_fun_friday_this_week,
)

# Management & enrollment API
from core.views.management import (
    api_get_teachers,
    create_group,
    create_teacher,
    gestion_view,
    language_cheque_students,
    update_enrollment_modality,
    update_site_config,
)

# Parents
from core.views.parents import ParentCreateView

# Payments
from core.views.payments import (
    create_payment,
    deactivate_payment,
    delete_payment,
    export_database_excel,
    export_payments,
    get_payment_details,
    parse_date_value,
    payment_detail,
    payment_detail_view,
    payment_statistics,
    payments_list,
    quick_complete_payment,
    search_parents,
    search_payments,
    update_payment,
    validate_student_parent,
)

# Schedule
from core.views.schedule import fun_friday_view, save_schedule_slot, schedule_view

# Students
from core.views.students import (
    StudentCreateView,
    StudentDetailView,
    StudentListView,
    StudentUpdateView,
    get_ff_student_ids,
    get_last_friday,
    get_next_friday,
    handle_student_form,
    search_students,
    student_detail,
    update_student,
)

# Support
from core.views.support import submit_support_ticket

# Todos & history
from core.views.todos import complete_todo, create_todo, history_list
