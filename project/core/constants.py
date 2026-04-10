"""
Core constants — shared locale data and scheduled app registry.
Pricing and billing constants live in billing/constants.py.
"""

# ============================================================================
# LOCALES - Nombres en español
# ============================================================================

DIAS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


# ============================================================================
# SCHEDULED APPS - Registry of scheduled apps/emails
# ============================================================================

SCHEDULED_APPS = [
    {"name": "Fun Friday", "url_name": "fun_friday_view", "frequency": "every_friday", "active": True},
    {"name": "Pago Mensual", "url_name": "payment_reminder_form", "frequency": "monthly_day_1", "active": True},
    {"name": "Vacaciones", "url_name": "vacation_closure_form", "frequency": "manual", "active": True},
    {"name": "Certificado Renta", "url_name": "tax_certificate_form", "frequency": "yearly_april", "active": True},
    {"name": "Informe Mensual", "url_name": "monthly_report_form", "frequency": "monthly_last_day", "active": True},
    {"name": "Bienvenida", "url_name": "welcome_form", "frequency": "on_student_creation", "active": True},
    {"name": "Cumpleaños", "url_name": "birthday_form", "frequency": "daily", "active": True},
    {"name": "Recibos", "url_name": "receipts_form", "frequency": "quarterly", "active": True},
    {"name": "Matrículas", "url_name": "enrollment_form", "frequency": "on_enrollment", "active": True},
]
