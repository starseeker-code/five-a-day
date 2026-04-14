from django.urls import path
from core.views import (
    # Auth
    login_view, logout_view, google_oauth_redirect, google_oauth_callback,
    # Dashboard
    home, all_info,
    # Schedule
    schedule_view, save_schedule_slot, fun_friday_view,
    # Todos
    create_todo, complete_todo,
    # History
    history_list,
    # Support
    submit_support_ticket,
    # Testing tools
    testing_tools_view, api_seed_database, api_create_backlog_task,
    api_update_backlog_task, api_toggle_error_email,
    # Error test pages
    test_error_400, test_error_403, test_error_404, test_error_405, test_error_500,
)

urlpatterns = [
    # Authentication
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("auth/google/", google_oauth_redirect, name="google_oauth_redirect"),
    path("auth/google/callback/", google_oauth_callback, name="google_oauth_callback"),
    # Dashboard
    path("", home, name="home"),
    path("database/", all_info, name="all_info"),
    # Schedule
    path("schedule/", schedule_view, name="schedule_view"),
    path("api/schedule/slot/save/", save_schedule_slot, name="save_schedule_slot"),
    path("fun-friday/", fun_friday_view, name="fun_friday_view"),
    # Todos
    path("api/todos/create/", create_todo, name="create_todo"),
    path("api/todos/<int:todo_id>/complete/", complete_todo, name="complete_todo"),
    # History
    path("api/history/", history_list, name="history_list"),
    # Support
    path("api/support/submit/", submit_support_ticket, name="submit_support_ticket"),
    # Testing tools
    path("testing/", testing_tools_view, name="testing_tools"),
    path("api/testing/seed/", api_seed_database, name="api_seed_database"),
    path("api/testing/backlog/create/", api_create_backlog_task, name="api_create_backlog_task"),
    path("api/testing/backlog/<int:task_id>/update/", api_update_backlog_task, name="api_update_backlog_task"),
    path("api/testing/error-email/toggle/", api_toggle_error_email, name="api_toggle_error_email"),
    # Error test pages
    path("400/", test_error_400, name="test_error_400"),
    path("403/", test_error_403, name="test_error_403"),
    path("404/", test_error_404, name="test_error_404"),
    path("405/", test_error_405, name="test_error_405"),
    path("500/", test_error_500, name="test_error_500"),
]
