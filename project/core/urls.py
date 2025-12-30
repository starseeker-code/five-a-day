from django.urls import path
from core.views import *

urlpatterns = [
    # ============================================================================
    # AUTHENTICATION - Autenticación
    # ============================================================================
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    
    # ============================================================================
    # HOME AND DASHBOARD
    # ============================================================================
    path("", home, name="home"),
    path("database/", all_info, name="all_info"),
    path("email/", email_test, name="email_test"),  # Prueba de emails
    
    # ============================================================================
    # PARENT MANAGEMENT - Gestión de Padres
    # ============================================================================
    path('parents/create/', ParentCreateView.as_view(), name='parent_create'),
    
    # ============================================================================
    # STUDENT MANAGEMENT - Gestión de Estudiantes
    # ============================================================================
    path('students/', StudentListView.as_view(), name='students_list'),
    path('students/create/', StudentCreateView.as_view(), name='student_create'),
    path('students/<int:student_id>/', StudentDetailView.as_view(), name='student_detail'),
    path('students/<int:student_id>/update/', StudentUpdateView.as_view(), name='student_update'),
    
    # ============================================================================
    # PAYMENT MANAGEMENT - Gestión de Pagos
    # ============================================================================
    path('payments/', payments_list, name='payments_list'),
    path('payments/create/', create_payment, name='create_payment'),
    path('payments/<int:payment_id>/', payment_detail_view, name='payment_detail_view'),
    path('payments/<int:payment_id>/update/', update_payment, name='update_payment'),
    path('payments/<int:payment_id>/delete/', delete_payment, name='delete_payment'),
    path('payments/<int:payment_id>/deactivate/', deactivate_payment, name='deactivate_payment'),
    
    # ============================================================================
    # API ENDPOINTS - AJAX Helper Functions
    # ============================================================================
    path('api/search/students/', search_students, name='search_students'),
    path('api/search/parents/', search_parents, name='search_parents'),
    path('api/validate/student-parent/', validate_student_parent, name='validate_student_parent'),
    path('api/search/payments/', search_payments, name='search_payments'),
    path('api/payments/<int:payment_id>/details/', get_payment_details, name='get_payment_details'),
    path('api/payments/statistics/', payment_statistics, name='payment_statistics'),
    path('payments/export/', export_payments, name='export_payments'),
    
    # ============================================================================
    # GESTIÓN - Configuración del Sitio, Profesores y Grupos
    # ============================================================================
    path('gestion/', gestion_view, name='gestion'),
    path('api/config/update/', update_site_config, name='update_site_config'),
    path('api/teachers/', api_get_teachers, name='api_get_teachers'),
    path('api/teachers/create/', create_teacher, name='create_teacher'),
    path('api/groups/create/', create_group, name='create_group'),
    
    # ============================================================================
    # APLICACIONES - Herramientas de comunicación
    # ============================================================================
    path('apps/fun-friday/', fun_friday_form, name='fun_friday_form'),
    
    # ============================================================================
    # SOPORTE - Sistema de tickets
    # ============================================================================
    path('api/support/submit/', submit_support_ticket, name='submit_support_ticket'),
]
