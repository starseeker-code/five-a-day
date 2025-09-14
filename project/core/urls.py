from django.urls import path
from core.views import *

urlpatterns = [
    path("", home, name="home"),  # type: ignore
    path("database/", all_info, name="all_info"),
    
    # Expense & Finance
    path("expense-categories/", expense_categories, name="expense-categories"),
    path("expenses/", expenses, name="expenses"),
    path("recurring-expense-templates/", recurring_expense_templates, name="recurring-expense-templates"),
    path("financial-periods/", financial_periods, name="financial-periods"),

    # Enrollment
    path("enrollment-types/", enrollment_types, name="enrollment-types"),
    path("enrollments/", enrollments, name="enrollments"),

    # Payments
    path("payments/", payments, name="payments"),

    # Payroll
    path("payrolls/", payrolls, name="payrolls"),

    # People
    path("teachers/", teachers, name="teachers"),
    path("groups/", groups, name="groups"),
    path("students/", students, name="students"),
    path("parents/", parents, name="parents"),
    
    # People.students
    path('students/<int:student_id>/', student_detail, name='student_detail'),
    path('students/<int:student_id>/update/', update_student, name='update_student'),
    
    # Payments.payment
    path('payments/create/', create_payment, name='create_payment'),
    path('payments/<int:payment_id>/', payment_detail, name='payment_detail'),
    path('payments/<int:payment_id>/update/', update_payment, name='update_payment'),
    path('payments/<int:payment_id>/detail/', payment_detail_view, name='payment_detail_view'),
    path('payments/<int:payment_id>/deactivate/', deactivate_payment, name='deactivate_payment'),
    
    # Payments.payment.rest
    path('api/search/students/', search_students, name='search_students'),
    path('api/search/parents/', search_parents, name='search_parents'),
    path('api/validate/student-parent/', validate_student_parent, name='validate_student_parent'),
    
    # Payments.payment.utils
    path('api/payments/statistics/', payment_statistics, name='payment_statistics'),
    path('payments/export/', export_payments, name='export_payments'),
]
