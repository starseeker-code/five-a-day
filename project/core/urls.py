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
]
