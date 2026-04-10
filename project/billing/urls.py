from django.urls import path
from core.views import (
    # Payments
    payments_list, create_payment, payment_detail_view, update_payment,
    delete_payment, deactivate_payment, quick_complete_payment,
    # Enrollment API
    update_enrollment_modality, language_cheque_students,
    # Search/API
    search_payments, get_payment_details, payment_statistics,
    export_payments, export_database_excel,
    # Management
    gestion_view, update_site_config, api_get_teachers, create_teacher, create_group,
)

urlpatterns = [
    # ============================================================================
    # PAYMENT MANAGEMENT - Gestión de Pagos
    # ============================================================================
    path("payments/", payments_list, name="payments_list"),
    path("payments/create/", create_payment, name="create_payment"),
    path("payments/<int:payment_id>/", payment_detail_view, name="payment_detail_view"),
    path("payments/<int:payment_id>/update/", update_payment, name="update_payment"),
    path("payments/<int:payment_id>/delete/", delete_payment, name="delete_payment"),
    path(
        "payments/<int:payment_id>/deactivate/",
        deactivate_payment,
        name="deactivate_payment",
    ),
    path(
        "api/payments/<int:payment_id>/quick-complete/",
        quick_complete_payment,
        name="quick_complete_payment",
    ),
    # ============================================================================
    # ENROLLMENT API
    # ============================================================================
    path(
        "api/students/<int:student_id>/enrollment/modality/",
        update_enrollment_modality,
        name="update_enrollment_modality",
    ),
    path(
        "api/students/language-cheque/",
        language_cheque_students,
        name="language_cheque_students",
    ),
    # ============================================================================
    # API ENDPOINTS - Search and Statistics
    # ============================================================================
    path("api/search/payments/", search_payments, name="search_payments"),
    path(
        "api/payments/<int:payment_id>/details/",
        get_payment_details,
        name="get_payment_details",
    ),
    path("api/payments/statistics/", payment_statistics, name="payment_statistics"),
    path("payments/export/", export_payments, name="export_payments"),
    path("database/export/", export_database_excel, name="export_database_excel"),
    # ============================================================================
    # GESTIÓN - Configuración del Sitio, Profesores y Grupos
    # ============================================================================
    path("management/", gestion_view, name="management"),
    path("api/config/update/", update_site_config, name="update_site_config"),
    path("api/teachers/", api_get_teachers, name="api_get_teachers"),
    path("api/teachers/create/", create_teacher, name="create_teacher"),
    path("api/groups/create/", create_group, name="create_group"),
]
