from django.urls import path

from core.views import (
    # Parents
    ParentCreateView,
    StudentCreateView,
    StudentDetailView,
    # Students
    StudentListView,
    StudentUpdateView,
    add_fun_friday_attendance,
    remove_fun_friday_attendance,
    search_parents,
    # Search/validation API
    search_students,
    # Fun Friday attendance
    toggle_fun_friday_this_week,
    validate_student_parent,
)

urlpatterns = [
    # ============================================================================
    # PARENT MANAGEMENT - Gestión de Padres
    # ============================================================================
    path("parents/create/", ParentCreateView.as_view(), name="parent_create"),
    # ============================================================================
    # STUDENT MANAGEMENT - Gestión de Estudiantes
    # ============================================================================
    path("students/", StudentListView.as_view(), name="students_list"),
    path("students/create/", StudentCreateView.as_view(), name="student_create"),
    path("students/<int:student_id>/", StudentDetailView.as_view(), name="student_detail"),
    path(
        "students/<int:student_id>/update/",
        StudentUpdateView.as_view(),
        name="student_update",
    ),
    path(
        "api/students/<int:student_id>/fun-friday/toggle/",
        toggle_fun_friday_this_week,
        name="toggle_fun_friday_this_week",
    ),
    path("api/students/<int:student_id>/fun-friday/add/", add_fun_friday_attendance, name="add_fun_friday_attendance"),
    path(
        "api/students/<int:student_id>/fun-friday/remove/",
        remove_fun_friday_attendance,
        name="remove_fun_friday_attendance",
    ),
    # ============================================================================
    # API ENDPOINTS - Search and Validation
    # ============================================================================
    path("api/search/students/", search_students, name="search_students"),
    path("api/search/parents/", search_parents, name="search_parents"),
    path(
        "api/validate/student-parent/",
        validate_student_parent,
        name="validate_student_parent",
    ),
]
