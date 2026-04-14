"""
Comando Django para enviar emails
Uso:
    python manage.py send_email --template happy_birthday --recipient user@example.com --subject "Feliz Cumpleaños"
    python manage.py send_email --template monthly_report --test
    python manage.py send_email --fun-friday --activity "Zumba en el parque" --date 2025-01-10 --time 17:00-18:30
    python manage.py send_email --payment-reminder --month enero
    python manage.py send_email --vacation-closure --reason "Navidad" --start 2025-12-23 --end 2025-01-07 --reopen 2025-01-08
    python manage.py send_email --tax-certificate --year 2024
    python manage.py send_email --tax-certificate --year 2024 --recipient email
"""

import json
from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from comms.services.email_functions import (
    send_all_tax_certificates,
    send_fun_friday_email,
    send_payment_reminder_email,
    send_quarterly_receipt_email,
    send_tax_certificate_email,
    send_vacation_closure_email,
)
from comms.services.email_service import email_service
from students.models import Parent, Student


class Command(BaseCommand):
    help = "Envía emails usando templates del sistema"

    def add_arguments(self, parser):
        parser.add_argument("--template", type=str, required=True, help="Nombre del template")
        parser.add_argument("--recipient", type=str, help="Email del destinatario")
        parser.add_argument("--subject", type=str, help="Asunto del email")
        parser.add_argument("--context", type=str, help="JSON con variables del template")
        parser.add_argument("--test", action="store_true", help="Envía email de prueba")
        parser.add_argument("--birthdays", action="store_true", help="Envía cumpleaños de hoy")
        parser.add_argument("--monthly-reports", action="store_true", help="Envía reportes mensuales")
        parser.add_argument("--fun-friday", action="store_true", help="Envía Fun Friday")
        parser.add_argument("--activity", type=str, help="Descripción actividad Fun Friday")
        parser.add_argument("--date", type=str, help="Fecha evento (YYYY-MM-DD)")
        parser.add_argument("--time", type=str, help="Horario (HH:MM-HH:MM)")
        parser.add_argument("--meeting-point", type=str, help="Punto de encuentro")
        parser.add_argument("--min-age", type=int, default=4, help="Edad mínima")
        parser.add_argument("--max-age", type=int, default=12, help="Edad máxima")
        parser.add_argument("--event-image", type=str, help="Ruta a imagen del evento")
        parser.add_argument("--payment-reminder", action="store_true", help="Recordatorio de pago")
        parser.add_argument("--month", type=str, help="Mes del pago")
        parser.add_argument("--payment-start", type=str, default="1", help="Día inicio pago")
        parser.add_argument("--payment-end", type=str, default="5", help="Día fin pago")
        parser.add_argument("--iban", type=str, default="ES00 0000 0000 0000 0000 0000")
        parser.add_argument("--cheque-idioma-price", type=str, default="40")
        parser.add_argument("--bizum-phone", type=str, default="613 481 141")
        parser.add_argument("--vacation-closure", action="store_true", help="Cierre vacaciones")
        parser.add_argument("--reason", type=str, help="Motivo del cierre")
        parser.add_argument("--start", type=str, help="Fecha inicio cierre")
        parser.add_argument("--end", type=str, help="Fecha fin cierre")
        parser.add_argument("--reopen", type=str, help="Fecha reapertura")
        parser.add_argument("--tax-certificate", action="store_true", help="Certificado fiscal")
        parser.add_argument("--year", type=int, help="Año fiscal")
        parser.add_argument("--quarterly-receipt", action="store_true", help="Recibo trimestral")
        parser.add_argument("--student-id", type=int, help="ID del estudiante")
        parser.add_argument("--months", type=str, help="Meses del trimestre (mes1,mes2,mes3)")

    def handle(self, *args, **options):
        template_name = options["template"]

        if options["test"]:
            self.send_test_email(template_name, options)
        elif options["birthdays"]:
            self.send_birthday_emails()
        elif options["monthly_reports"]:
            self.send_monthly_reports()
        elif options["fun_friday"]:
            self.send_fun_friday_emails(options)
        elif options["payment_reminder"]:
            self.send_payment_reminder_emails(options)
        elif options["vacation_closure"]:
            self.send_vacation_closure_emails(options)
        elif options["tax_certificate"]:
            self.send_tax_certificate_email_cmd(options)
        elif options["quarterly_receipt"]:
            self.send_quarterly_receipt(options)
        elif options["recipient"]:
            self.send_single_email(template_name, options)
        else:
            raise CommandError("Se requiere --recipient (o usa --test para prueba)")

    def send_test_email(self, template_name, options):
        recipient = settings.EMAIL_HOST_USER
        subject = options.get("subject") or f"Test Email - {template_name}"
        context = {
            "name": "Usuario de Prueba",
            "student_name": "Estudiante Test",
            "amount": 100.50,
            "due_date": "31/12/2025",
        }
        if options.get("context"):
            try:
                context.update(json.loads(options["context"]))
            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING("Context JSON inválido, usando valores por defecto"))
        self.stdout.write(f"Enviando email de prueba a {recipient}...")
        success = email_service.send_email(
            template_name=template_name, recipients=recipient, subject=subject, context=context
        )
        self.stdout.write(self.style.SUCCESS("Email enviado") if success else self.style.ERROR("Error al enviar"))

    def send_single_email(self, template_name, options):
        recipient = options["recipient"]
        subject = options.get("subject") or "Five a Day"
        context = json.loads(options["context"]) if options.get("context") else {}
        success = email_service.send_email(
            template_name=template_name, recipients=recipient, subject=subject, context=context
        )
        self.stdout.write(self.style.SUCCESS("Email enviado") if success else self.style.ERROR("Error al enviar"))

    def send_birthday_emails(self):
        today = date.today()
        birthday_students = Student.objects.filter(
            birth_date__month=today.month, birth_date__day=today.day, active=True
        ).prefetch_related("parents")
        if not birthday_students.exists():
            self.stdout.write(self.style.WARNING("No hay cumpleaños hoy"))
            return
        sent, failed = 0, 0
        for student in birthday_students:
            parent = student.parents.exclude(email="").exclude(email__isnull=True).first()
            if not parent:
                failed += 1
                continue
            success = email_service.send_email(
                template_name="happy_birthday",
                recipients=parent.email,
                subject=f"¡Feliz Cumpleaños {student.first_name}!",
                context={"name": student.first_name},
            )
            sent += 1 if success else 0
            failed += 0 if success else 1
        self.stdout.write(self.style.SUCCESS(f"Resultado: {sent} enviados, {failed} fallidos"))

    def send_monthly_reports(self):
        parents = Parent.objects.filter(email__isnull=False).exclude(email="")
        if not parents.exists():
            self.stdout.write(self.style.WARNING("No hay padres con email"))
            return
        sent, failed = 0, 0
        for parent in parents:
            students = parent.children.filter(active=True)
            context = {
                "parent_name": parent.full_name,
                "students": [
                    {"name": s.full_name, "group": s.group.group_name if s.group else "Sin grupo"} for s in students
                ],
                "total_students": students.count(),
            }
            success = email_service.send_email(
                template_name="monthly_report",
                recipients=parent.email,
                subject="Reporte Mensual - Five a Day",
                context=context,
            )
            sent += 1 if success else 0
            failed += 0 if success else 1
        self.stdout.write(self.style.SUCCESS(f"Resultado: {sent} enviados, {failed} fallidos"))

    def send_fun_friday_emails(self, options):
        if not options.get("activity"):
            raise CommandError("Se requiere --activity")
        if not options.get("date"):
            raise CommandError("Se requiere --date (YYYY-MM-DD)")
        if not options.get("time"):
            raise CommandError("Se requiere --time (HH:MM-HH:MM)")
        try:
            event_date = datetime.strptime(options["date"], "%Y-%m-%d")
        except ValueError as err:
            raise CommandError("Formato de fecha inválido") from err
        start_time, end_time = options["time"].split("-")
        DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        MONTHS_ES = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        parents = Parent.objects.filter(email__isnull=False, children__active=True).distinct()
        recipient_emails = [p.email for p in parents if p.email]
        success = send_fun_friday_email(
            recipients=recipient_emails,
            day_name=DAYS_ES[event_date.weekday()],
            day_number=event_date.day,
            month=MONTHS_ES[event_date.month - 1],
            start_time=start_time,
            end_time=end_time,
            activity_description=options["activity"],
            minimum_age=options.get("min_age", 4),
            maximum_age=options.get("max_age", 12),
            meeting_point=options.get("meeting_point"),
            event_image_path=options.get("event_image"),
        )
        self.stdout.write(
            self.style.SUCCESS(f"Enviado a {len(recipient_emails)} padres") if success else self.style.ERROR("Error")
        )

    def send_payment_reminder_emails(self, options):
        if not options.get("month"):
            raise CommandError("Se requiere --month")
        DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        parents = Parent.objects.filter(email__isnull=False, children__active=True).exclude(email="").distinct()
        recipient_emails = list(parents.values_list("email", flat=True))
        success = send_payment_reminder_email(
            recipients=recipient_emails,
            payment_start_day_name=DAYS_ES[0],
            payment_start_day_number=int(options.get("payment_start", 1)),
            payment_end_day_name=DAYS_ES[4],
            payment_end_day_number=int(options.get("payment_end", 5)),
            month=options["month"],
            iban_number=options.get("iban", ""),
            reduced_price_cheque_idioma=options.get("cheque_idioma_price", "40"),
            telephone_number_bizum=options.get("bizum_phone", ""),
        )
        self.stdout.write(
            self.style.SUCCESS(f"Enviado a {len(recipient_emails)} padres") if success else self.style.ERROR("Error")
        )

    def send_vacation_closure_emails(self, options):
        for field in ("reason", "start", "end", "reopen"):
            if not options.get(field):
                raise CommandError(f"Se requiere --{field}")
        start_date = datetime.strptime(options["start"], "%Y-%m-%d")
        end_date = datetime.strptime(options["end"], "%Y-%m-%d")
        reopen_date = datetime.strptime(options["reopen"], "%Y-%m-%d")
        DAYS_ES = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
        MONTHS_ES = [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
        parents = Parent.objects.filter(email__isnull=False, children__active=True).exclude(email="").distinct()
        recipient_emails = list(parents.values_list("email", flat=True))
        success = send_vacation_closure_email(
            recipients=recipient_emails,
            start_closure_day_name=DAYS_ES[start_date.weekday()],
            start_closure_day_number=start_date.day,
            end_closure_day_name=DAYS_ES[end_date.weekday()],
            end_closure_day_number=end_date.day,
            month_closure=MONTHS_ES[start_date.month - 1],
            closure_reason=options["reason"],
            reopening_day_name=DAYS_ES[reopen_date.weekday()],
            reopening_day_number=reopen_date.day,
            month_reopening=MONTHS_ES[reopen_date.month - 1],
        )
        self.stdout.write(
            self.style.SUCCESS(f"Enviado a {len(recipient_emails)} padres") if success else self.style.ERROR("Error")
        )

    def send_tax_certificate_email_cmd(self, options):
        if not options.get("year"):
            raise CommandError("Se requiere --year")
        year = options["year"]
        if options.get("recipient"):
            try:
                parent = Parent.objects.get(email=options["recipient"])
            except Parent.DoesNotExist as err:
                raise CommandError(f"No se encontró padre con email {options['recipient']}") from err
            success = send_tax_certificate_email(parent=parent, year=year)
            self.stdout.write(
                self.style.SUCCESS(f"Certificado enviado a {parent.email}") if success else self.style.ERROR("Error")
            )
        else:
            results = send_all_tax_certificates(year)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Resultado: {results['sent']} enviados, {results['skipped']} omitidos, {results['failed']} fallidos"
                )
            )

    def send_quarterly_receipt(self, options):
        if not options.get("student_id"):
            raise CommandError("Se requiere --student-id")
        if not options.get("months"):
            raise CommandError("Se requiere --months (mes1,mes2,mes3)")
        student = Student.objects.get(pk=options["student_id"])
        parent = student.parents.exclude(email="").exclude(email__isnull=True).first()
        if not parent:
            raise CommandError(f"{student.full_name} no tiene padre con email")
        months = options["months"].split(",")
        if len(months) != 3:
            raise CommandError("Se requieren exactamente 3 meses")
        success = send_quarterly_receipt_email(
            parent_email=parent.email,
            student_name=student.full_name,
            month_1=months[0].strip(),
            month_2=months[1].strip(),
            month_3=months[2].strip(),
        )
        self.stdout.write(self.style.SUCCESS("Recibo enviado") if success else self.style.ERROR("Error"))
