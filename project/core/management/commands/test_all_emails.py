"""
Envía un email de prueba de cada app al SUPPORT_EMAIL.

Uso:
    python manage.py test_all_emails           # Envía todos
    python manage.py test_all_emails --only fun_friday,birthday  # Solo algunos
    python manage.py test_all_emails --list     # Lista las apps disponibles
    python manage.py test_all_emails --to other@email.com  # Otro destinatario
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from datetime import date, timedelta

# ============================================================================
# LISTA DE APPS DE EMAIL
# Para añadir una nueva app, añade una entrada aquí con:
#   - key:          identificador corto
#   - template:     nombre del template (sin .html)
#   - subject:      asunto del email
#   - context:      dict con datos de ejemplo para el template
#   - description:  descripción corta para --list
# ============================================================================
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
         "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

today = date.today()
next_friday = today + timedelta(days=(4 - today.weekday()) % 7 or 7)


def get_email_apps():
    """Retorna la lista de apps de email con sus datos de prueba."""
    return [
        {
            "key": "fun_friday",
            "template": "fun_friday",
            "subject": f"🧪 [TEST] Fun Friday - {DIAS[next_friday.weekday()]} {next_friday.day} de {MESES[next_friday.month - 1]}",
            "context": {
                "day_name": DIAS[next_friday.weekday()],
                "day_number": next_friday.day,
                "month": MESES[next_friday.month - 1],
                "start_time": "17:00",
                "end_time": "18:30",
                "activity_description": "<strong>🎨 ¡SESIÓN DE MANUALIDADES!</strong><br><br>Esta semana haremos manualidades creativas con materiales reciclados.",
                "meeting_point": "En la puerta principal del centro",
                "minimum_age": 5,
                "maximum_age": 12,
            },
            "description": "Invitación Fun Friday (semanal, manual)",
        },
        {
            "key": "payment_reminder",
            "template": "recordatorio_pago_mensual_trimestral",
            "subject": f"🧪 [TEST] Recordatorio de Pago - {MESES[today.month - 1]}",
            "context": {
                "payment_start_day_name": DIAS[today.replace(day=1).weekday()],
                "payment_start_day_number": 1,
                "payment_end_day_name": DIAS[today.replace(day=5).weekday()],
                "payment_end_day_number": 5,
                "month": MESES[today.month - 1],
                "iban_number": "ES00 0000 0000 0000 0000 0000",
                "reduced_price_cheque_idioma": "34€",
                "telephone_number_bizum": "613 481 141",
            },
            "description": "Recordatorio de pago (día 1 de cada mes, automático)",
        },
        {
            "key": "vacation_closure",
            "template": "recordatorio_cierre_vacaciones",
            "subject": "🧪 [TEST] Cierre por Navidad - Five a Day",
            "context": {
                "start_closure_day_name": "lunes",
                "start_closure_day_number": 23,
                "end_closure_day_name": "viernes",
                "end_closure_day_number": 3,
                "month_closure": "diciembre",
                "closure_reason": "Navidad",
                "reopening_day_name": "lunes",
                "reopening_day_number": 8,
                "month_reopening": "enero",
            },
            "description": "Aviso de cierre por vacaciones (manual)",
        },
        {
            "key": "tax_certificate",
            "template": "certificado_renta",
            "subject": f"🧪 [TEST] Certificado Fiscal {today.year - 1} - Five a Day",
            "context": {
                "year": today.year - 1,
                "parent_name": "Padre de Prueba",
            },
            "description": "Certificado fiscal anual (abril, semi-automático)",
        },
        {
            "key": "monthly_report",
            "template": "monthly_report",
            "subject": "🧪 [TEST] Informe Mensual - Five a Day",
            "context": {
                "month": MESES[today.month - 1],
                "year": today.year,
                "parent_name": "Padre de Prueba",
                "students": [
                    {"name": "Alumno Ejemplo 1", "group": "Grupo A"},
                    {"name": "Alumno Ejemplo 2", "group": "Grupo B"},
                ],
                "total_students": 2,
            },
            "description": "Informe mensual (día 28, automático)",
        },
        {
            "key": "welcome",
            "template": "welcome_student",
            "subject": "🧪 [TEST] ¡Bienvenido/a Alumno Test a Five a Day!",
            "context": {
                "parent_name": "Padre de Prueba",
                "student_name": "Alumno Test",
                "group_name": "Grupo A",
                "enrollment_type": "Mensual",
                "schedule_type": "Jornada completa (2 clases/semana)",
                "start_date": "01/09/2025",
            },
            "description": "Bienvenida al nuevo alumno (al crear estudiante, evento)",
        },
        {
            "key": "birthday",
            "template": "happy_birthday",
            "subject": "🧪 [TEST] ¡Feliz Cumpleaños Alumno!",
            "context": {
                "name": "Alumno de Prueba",
            },
            "description": "Cumpleaños (diario 8:00 AM, automático)",
        },
        {
            "key": "receipt_quarterly",
            "template": "recibo_trimestre_niño",
            "subject": "🧪 [TEST] Recibo Trimestral - Alumno Test",
            "context": {
                "student_name": "Alumno de Prueba",
                "month_1": "enero",
                "month_2": "febrero",
                "month_3": "marzo",
            },
            "description": "Recibo trimestral niños (ene/abr/jul/oct, semi-automático)",
        },
        {
            "key": "receipt_adult",
            "template": "recibo_adulto",
            "subject": f"🧪 [TEST] Recibo Mensual - {MESES[today.month - 1].title()}",
            "context": {
                "month": MESES[today.month - 1],
            },
            "description": "Recibo mensual adultos (día 1, semi-automático)",
        },
        {
            "key": "enrollment_child",
            "template": "matricula_niño",
            "subject": "🧪 [TEST] Confirmación de Matrícula - Alumno Test",
            "context": {
                "student": "Alumno de Prueba",
                "genero": "m",
                "academic_year": f"{today.year}-{today.year + 1}",
                "month": "septiembre",
            },
            "description": "Confirmación matrícula niño (al confirmar, evento)",
        },
        {
            "key": "enrollment_adult",
            "template": "matricula_adulto",
            "subject": "🧪 [TEST] Confirmación de Matrícula Adulto",
            "context": {
                "genero": "f",
                "academic_year": f"{today.year}-{today.year + 1}",
                "month": "septiembre",
            },
            "description": "Confirmación matrícula adulto (al confirmar, evento)",
        },
    ]


class Command(BaseCommand):
    help = "Envía un email de prueba de cada app al SUPPORT_EMAIL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            help="Email destinatario (default: SUPPORT_EMAIL del .env)",
        )
        parser.add_argument(
            "--only",
            type=str,
            help="Enviar solo estas apps, separadas por coma (ej: fun_friday,birthday)",
        )
        parser.add_argument(
            "--exclude",
            type=str,
            help="Excluir estas apps, separadas por coma",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            help="Solo listar las apps disponibles, sin enviar",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Segundos de espera entre emails (default: 1.0)",
        )

    def handle(self, *args, **options):
        import time

        apps = get_email_apps()
        recipient = options.get("to") or getattr(settings, "SUPPORT_EMAIL", None)

        if not recipient:
            self.stderr.write(self.style.ERROR(
                "❌ No hay SUPPORT_EMAIL en .env ni se pasó --to"
            ))
            return

        # --list: solo mostrar apps
        if options["list"]:
            self.stdout.write("\n📧 Apps de email disponibles:\n")
            for i, app in enumerate(apps, 1):
                self.stdout.write(f"  {i:2d}. {app['key']:25s} {app['description']}")
            self.stdout.write(f"\nTotal: {len(apps)} apps\n")
            return

        # Filtrar apps
        if options.get("only"):
            keys = [k.strip() for k in options["only"].split(",")]
            apps = [a for a in apps if a["key"] in keys]
            unknown = set(keys) - {a["key"] for a in apps}
            if unknown:
                self.stderr.write(self.style.WARNING(
                    f"⚠️  Apps no encontradas: {', '.join(unknown)}"
                ))

        if options.get("exclude"):
            exclude_keys = [k.strip() for k in options["exclude"].split(",")]
            apps = [a for a in apps if a["key"] not in exclude_keys]

        if not apps:
            self.stderr.write(self.style.WARNING("⚠️  No hay apps para enviar"))
            return

        # Enviar
        from core.email import email_service

        self.stdout.write(f"\n📧 Enviando {len(apps)} emails de prueba a {recipient}\n")
        self.stdout.write("─" * 60)

        sent = 0
        failed = 0
        delay = options["delay"]

        for i, app in enumerate(apps, 1):
            self.stdout.write(
                f"  [{i}/{len(apps)}] {app['key']:25s} ", ending=""
            )
            try:
                success = email_service.send_email(
                    template_name=app["template"],
                    recipients=recipient,
                    subject=app["subject"],
                    context=app["context"],
                )
                if success:
                    sent += 1
                    self.stdout.write(self.style.SUCCESS("✅"))
                else:
                    failed += 1
                    self.stdout.write(self.style.ERROR("❌ (send returned False)"))
            except Exception as e:
                failed += 1
                self.stdout.write(self.style.ERROR(f"❌ {e}"))

            # Pausa entre emails para no saturar SMTP
            if i < len(apps) and delay > 0:
                time.sleep(delay)

        self.stdout.write("─" * 60)
        self.stdout.write(
            self.style.SUCCESS(f"\n📊 Resultado: {sent} enviados, {failed} fallidos")
        )
        self.stdout.write(f"📬 Revisa la bandeja de {recipient}\n")
