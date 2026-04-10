"""
URL patterns for the comms app.
Handles app form views for email/communication tools.

Views are still in core.views for now -- only the URL routing moves here.
"""
from django.urls import path
from core.views import (
    apps_view, fun_friday_form, payment_reminder_form, vacation_closure_form,
    tax_certificate_form, monthly_report_form, welcome_form, birthday_form,
    receipts_form, enrollment_form,
)

urlpatterns = [
    # ============================================================================
    # APLICACIONES - Herramientas de comunicacion
    # ============================================================================
    path("apps/", apps_view, name="apps"),
    path("apps/fun-friday/", fun_friday_form, name="fun_friday_form"),
    path("apps/payment-reminder/", payment_reminder_form, name="payment_reminder_form"),
    path("apps/vacation-closure/", vacation_closure_form, name="vacation_closure_form"),
    path("apps/tax-certificate/", tax_certificate_form, name="tax_certificate_form"),
    path("apps/monthly-report/", monthly_report_form, name="monthly_report_form"),
    path("apps/welcome/", welcome_form, name="welcome_form"),
    path("apps/birthday/", birthday_form, name="birthday_form"),
    path("apps/receipts/", receipts_form, name="receipts_form"),
    path("apps/enrollment/", enrollment_form, name="enrollment_form"),
]
