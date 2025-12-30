"""
Comando Django para enviar emails
Uso:
    python manage.py send_email --template happy_birthday --recipient user@example.com --subject "Feliz Cumpleaños"
    python manage.py send_email --template monthly_report --test
    python manage.py send_email --fun-friday --activity "Zumba en el parque" --date 2025-01-10 --time 17:00-18:30
    python manage.py send_email --payment-reminder --month enero
    python manage.py send_email --vacation-closure --reason "Navidad" --start 2025-12-23 --end 2025-01-07 --reopen 2025-01-08
    python manage.py send_email --tax-certificate --year 2024                    # Envía a TODOS los padres
    python manage.py send_email --tax-certificate --year 2024 --recipient email  # Envía solo a un padre
"""
from django.core.management.base import BaseCommand, CommandError
from core.email import (
    email_service,
    send_fun_friday_email,
    send_payment_reminder_email,
    send_vacation_closure_email,
    send_tax_certificate_email,
    send_quarterly_receipt_email,
    send_enrollment_confirmation_email,
)
from core.models import Student, Parent
from django.conf import settings
import json
import os
from datetime import datetime, date


class Command(BaseCommand):
    help = 'Envía emails usando templates del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--template',
            type=str,
            required=True,
            help='Nombre del template a usar (ej: happy_birthday, payment_reminder)'
        )
        
        parser.add_argument(
            '--recipient',
            type=str,
            help='Email del destinatario'
        )
        
        parser.add_argument(
            '--subject',
            type=str,
            help='Asunto del email'
        )
        
        parser.add_argument(
            '--context',
            type=str,
            help='JSON con variables del template. Ej: \'{"name": "Juan", "amount": 100}\''
        )
        
        parser.add_argument(
            '--test',
            action='store_true',
            help='Envía email de prueba al EMAIL_HOST_USER configurado'
        )
        
        parser.add_argument(
            '--birthdays',
            action='store_true',
            help='Envía emails de cumpleaños a estudiantes que cumplen hoy'
        )
        
        parser.add_argument(
            '--monthly-reports',
            action='store_true',
            help='Envía reportes mensuales a todos los padres'
        )
        
        # =====================================================================
        # FUN FRIDAY
        # =====================================================================
        parser.add_argument(
            '--fun-friday',
            action='store_true',
            help='Envía invitación a Fun Friday a todos los padres'
        )
        parser.add_argument(
            '--activity',
            type=str,
            help='Descripción de la actividad del Fun Friday'
        )
        parser.add_argument(
            '--date',
            type=str,
            help='Fecha del evento (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--time',
            type=str,
            help='Horario (formato: HH:MM-HH:MM, ej: 17:00-18:30)'
        )
        parser.add_argument(
            '--meeting-point',
            type=str,
            help='Punto de encuentro (opcional)'
        )
        parser.add_argument(
            '--min-age',
            type=int,
            default=4,
            help='Edad mínima (default: 4)'
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=12,
            help='Edad máxima (default: 12)'
        )
        parser.add_argument(
            '--event-image',
            type=str,
            help='Ruta a la imagen del evento (opcional)'
        )
        
        # =====================================================================
        # PAYMENT REMINDER
        # =====================================================================
        parser.add_argument(
            '--payment-reminder',
            action='store_true',
            help='Envía recordatorio de pago a todos los padres'
        )
        parser.add_argument(
            '--month',
            type=str,
            help='Mes del pago (ej: enero, febrero...)'
        )
        parser.add_argument(
            '--payment-start',
            type=str,
            default='1',
            help='Día inicio del período de pago (default: 1)'
        )
        parser.add_argument(
            '--payment-end',
            type=str,
            default='5',
            help='Día fin del período de pago (default: 5)'
        )
        parser.add_argument(
            '--iban',
            type=str,
            default='ES00 0000 0000 0000 0000 0000',
            help='Número IBAN para transferencias'
        )
        parser.add_argument(
            '--cheque-idioma-price',
            type=str,
            default='40',
            help='Precio reducido con cheque idioma'
        )
        parser.add_argument(
            '--bizum-phone',
            type=str,
            default='613 481 141',
            help='Teléfono para Bizum'
        )
        
        # =====================================================================
        # VACATION CLOSURE
        # =====================================================================
        parser.add_argument(
            '--vacation-closure',
            action='store_true',
            help='Envía aviso de cierre por vacaciones'
        )
        parser.add_argument(
            '--reason',
            type=str,
            help='Motivo del cierre (ej: Navidad, Semana Santa)'
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Fecha inicio del cierre (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end',
            type=str,
            help='Fecha fin del cierre (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--reopen',
            type=str,
            help='Fecha de reapertura (YYYY-MM-DD)'
        )
        
        # =====================================================================
        # TAX CERTIFICATE
        # =====================================================================
        parser.add_argument(
            '--tax-certificate',
            action='store_true',
            help='Genera y envía certificado fiscal (PDF automático con todos los pagos del año)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Año fiscal del certificado'
        )
        # --recipient es opcional: si se omite, se envía a TODOS los padres con pagos
        
        # =====================================================================
        # QUARTERLY RECEIPT
        # =====================================================================
        parser.add_argument(
            '--quarterly-receipt',
            action='store_true',
            help='Envía recibo trimestral'
        )
        parser.add_argument(
            '--student-id',
            type=int,
            help='ID del estudiante'
        )
        parser.add_argument(
            '--months',
            type=str,
            help='Meses del trimestre (formato: mes1,mes2,mes3)'
        )

    def handle(self, *args, **options):
        template_name = options['template']
        
        # Modo TEST: Enviar a ti mismo
        if options['test']:
            self.send_test_email(template_name, options)
            return
        
        # Modo CUMPLEAÑOS: Enviar a estudiantes que cumplen hoy
        if options['birthdays']:
            self.send_birthday_emails()
            return
        
        # Modo REPORTES MENSUALES: Enviar a todos los padres
        if options['monthly_reports']:
            self.send_monthly_reports()
            return
        
        # Modo FUN FRIDAY: Enviar invitación a todos los padres
        if options['fun_friday']:
            self.send_fun_friday_emails(options)
            return
        
        # Modo PAYMENT REMINDER: Enviar recordatorio de pago
        if options['payment_reminder']:
            self.send_payment_reminder_emails(options)
            return
        
        # Modo VACATION CLOSURE: Enviar aviso de cierre
        if options['vacation_closure']:
            self.send_vacation_closure_emails(options)
            return
        
        # Modo TAX CERTIFICATE: Enviar certificado de renta
        if options['tax_certificate']:
            self.send_tax_certificate_email(options)
            return
        
        # Modo QUARTERLY RECEIPT: Enviar recibo trimestral
        if options['quarterly_receipt']:
            self.send_quarterly_receipt(options)
            return
        
        # Modo MANUAL: Enviar un email específico
        if not options['recipient']:
            raise CommandError('Se requiere --recipient (o usa --test para prueba)')
        
        self.send_single_email(template_name, options)

    def send_test_email(self, template_name, options):
        """Envía email de prueba al EMAIL_HOST_USER"""
        recipient = settings.EMAIL_HOST_USER
        subject = options.get('subject') or f'🧪 Test Email - {template_name}'
        
        # Context por defecto para testing
        context = {
            'name': 'Usuario de Prueba',
            'student_name': 'Estudiante Test',
            'amount': 100.50,
            'due_date': '31/12/2025'
        }
        
        # Sobrescribir con context personalizado si existe
        if options.get('context'):
            try:
                custom_context = json.loads(options['context'])
                context.update(custom_context)
            except json.JSONDecodeError:
                self.stdout.write(self.style.WARNING('⚠️  Context JSON inválido, usando valores por defecto'))
        
        self.stdout.write(f'📧 Enviando email de prueba a {recipient}...')
        
        success = email_service.send_email(
            template_name=template_name,
            recipients=recipient,
            subject=subject,
            context=context
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Email de prueba enviado correctamente'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Error al enviar email de prueba'))

    def send_single_email(self, template_name, options):
        """Envía un email individual"""
        recipient = options['recipient']
        subject = options.get('subject') or 'Five a Day'
        
        context = {}
        if options.get('context'):
            try:
                context = json.loads(options['context'])
            except json.JSONDecodeError:
                raise CommandError('Context debe ser un JSON válido')
        
        self.stdout.write(f'📧 Enviando email a {recipient}...')
        
        success = email_service.send_email(
            template_name=template_name,
            recipients=recipient,
            subject=subject,
            context=context
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Email enviado correctamente'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ Error al enviar email'))

    def send_birthday_emails(self):
        """Envía emails de cumpleaños a estudiantes que cumplen hoy"""
        from datetime import date
        
        today = date.today()
        
        # Buscar estudiantes activos que cumplen hoy
        birthday_students = Student.objects.filter(
            birth_date__month=today.month,
            birth_date__day=today.day,
            active=True
        ).prefetch_related('parents')
        
        if not birthday_students.exists():
            self.stdout.write(self.style.WARNING('ℹ️  No hay cumpleaños hoy'))
            return
        
        self.stdout.write(f'🎂 Encontrados {birthday_students.count()} cumpleaños hoy')
        
        sent = 0
        failed = 0
        
        for student in birthday_students:
            # Obtener el primer padre con email
            parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
            
            if not parent:
                self.stdout.write(self.style.WARNING(f'⚠️  {student.full_name}: Sin email del padre'))
                failed += 1
                continue
            
            success = email_service.send_email(
                template_name='happy_birthday',
                recipients=parent.email,
                subject=f'🎉 ¡Feliz Cumpleaños {student.first_name}!',
                context={'name': student.first_name}
            )
            
            if success:
                sent += 1
                self.stdout.write(f'  ✅ {student.full_name} → {parent.email}')
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {student.full_name} → {parent.email}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Resultado: {sent} enviados, {failed} fallidos'))

    def send_monthly_reports(self):
        """Envía reportes mensuales a todos los padres"""
        parents = Parent.objects.filter(email__isnull=False).exclude(email='')
        
        if not parents.exists():
            self.stdout.write(self.style.WARNING('ℹ️  No hay padres con email'))
            return
        
        self.stdout.write(f'📊 Enviando reportes a {parents.count()} padres...')
        
        sent = 0
        failed = 0
        
        for parent in parents:
            # Obtener estudiantes asociados a este padre
            students = parent.children.filter(active=True)
            
            context = {
                'parent_name': parent.full_name,
                'students': [
                    {
                        'name': s.full_name,
                        'group': s.group.group_name if s.group else 'Sin grupo'
                    }
                    for s in students
                ],
                'total_students': students.count()
            }
            
            success = email_service.send_email(
                template_name='monthly_report',
                recipients=parent.email,
                subject='📊 Reporte Mensual - Five a Day',
                context=context
            )
            
            if success:
                sent += 1
                self.stdout.write(f'  ✅ {parent.full_name} → {parent.email}')
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {parent.full_name} → {parent.email}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Resultado: {sent} enviados, {failed} fallidos'))

    def send_fun_friday_emails(self, options):
        """Envía invitaciones a Fun Friday a todos los padres elegibles"""
        
        if not options.get('activity'):
            raise CommandError('Se requiere --activity para Fun Friday')
        if not options.get('date'):
            raise CommandError('Se requiere --date (YYYY-MM-DD) para Fun Friday')
        if not options.get('time'):
            raise CommandError('Se requiere --time (HH:MM-HH:MM) para Fun Friday')
        
        # Parsear fecha
        try:
            event_date = datetime.strptime(options['date'], '%Y-%m-%d')
        except ValueError:
            raise CommandError('Formato de fecha inválido. Usa YYYY-MM-DD')
        
        # Parsear horario
        try:
            start_time, end_time = options['time'].split('-')
        except ValueError:
            raise CommandError('Formato de horario inválido. Usa HH:MM-HH:MM')
        
        # Nombres de días y meses en español
        DAYS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        day_name = DAYS_ES[event_date.weekday()]
        month_name = MONTHS_ES[event_date.month - 1]
        
        min_age = options.get('min_age', 4)
        max_age = options.get('max_age', 12)
        
        # Obtener todos los padres con estudiantes activos en el rango de edad
        parents = Parent.objects.filter(
            email__isnull=False,
            children__active=True,
            children__birth_date__isnull=False
        ).distinct()
        
        # Filtrar por edad
        today = date.today()
        eligible_parents = []
        for parent in parents:
            for student in parent.children.filter(active=True):
                age = today.year - student.birth_date.year - (
                    (today.month, today.day) < (student.birth_date.month, student.birth_date.day)
                )
                if min_age <= age <= max_age:
                    eligible_parents.append(parent)
                    break
        
        if not eligible_parents:
            self.stdout.write(self.style.WARNING('ℹ️  No hay padres elegibles'))
            return
        
        self.stdout.write(f'🎉 Enviando Fun Friday a {len(eligible_parents)} padres...')
        
        # Obtener emails
        recipient_emails = [p.email for p in eligible_parents]
        
        success = send_fun_friday_email(
            recipients=recipient_emails,
            day_name=day_name,
            day_number=event_date.day,
            month=month_name,
            start_time=start_time,
            end_time=end_time,
            activity_description=options['activity'],
            minimum_age=min_age,
            maximum_age=max_age,
            meeting_point=options.get('meeting_point'),
            event_image_path=options.get('event_image')
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Invitación enviada a {len(recipient_emails)} padres'))
        else:
            self.stdout.write(self.style.ERROR('❌ Error al enviar invitaciones'))

    def send_payment_reminder_emails(self, options):
        """Envía recordatorio de pago a todos los padres"""
        
        if not options.get('month'):
            raise CommandError('Se requiere --month para recordatorio de pago')
        
        DAYS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        
        # Obtener todos los padres con estudiantes activos
        parents = Parent.objects.filter(
            email__isnull=False,
            children__active=True
        ).exclude(email='').distinct()
        
        if not parents.exists():
            self.stdout.write(self.style.WARNING('ℹ️  No hay padres con estudiantes activos'))
            return
        
        self.stdout.write(f'💳 Enviando recordatorio de pago a {parents.count()} padres...')
        
        recipient_emails = list(parents.values_list('email', flat=True))
        
        success = send_payment_reminder_email(
            recipients=recipient_emails,
            payment_start_day_name=DAYS_ES[0],  # Se puede mejorar
            payment_start_day_number=int(options.get('payment_start', 1)),
            payment_end_day_name=DAYS_ES[4],  # Se puede mejorar
            payment_end_day_number=int(options.get('payment_end', 5)),
            month=options['month'],
            iban_number=options.get('iban', 'ES00 0000 0000 0000 0000 0000'),
            reduced_price_cheque_idioma=options.get('cheque_idioma_price', '40'),
            telephone_number_bizum=options.get('bizum_phone', '613 481 141')
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Recordatorio enviado a {len(recipient_emails)} padres'))
        else:
            self.stdout.write(self.style.ERROR('❌ Error al enviar recordatorios'))

    def send_vacation_closure_emails(self, options):
        """Envía aviso de cierre por vacaciones"""
        
        if not options.get('reason'):
            raise CommandError('Se requiere --reason para cierre de vacaciones')
        if not options.get('start'):
            raise CommandError('Se requiere --start (YYYY-MM-DD) para inicio de cierre')
        if not options.get('end'):
            raise CommandError('Se requiere --end (YYYY-MM-DD) para fin de cierre')
        if not options.get('reopen'):
            raise CommandError('Se requiere --reopen (YYYY-MM-DD) para reapertura')
        
        # Parsear fechas
        try:
            start_date = datetime.strptime(options['start'], '%Y-%m-%d')
            end_date = datetime.strptime(options['end'], '%Y-%m-%d')
            reopen_date = datetime.strptime(options['reopen'], '%Y-%m-%d')
        except ValueError:
            raise CommandError('Formato de fecha inválido. Usa YYYY-MM-DD')
        
        DAYS_ES = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                     'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        # Obtener todos los padres
        parents = Parent.objects.filter(
            email__isnull=False,
            children__active=True
        ).exclude(email='').distinct()
        
        if not parents.exists():
            self.stdout.write(self.style.WARNING('ℹ️  No hay padres'))
            return
        
        self.stdout.write(f'🏖️ Enviando aviso de cierre a {parents.count()} padres...')
        
        recipient_emails = list(parents.values_list('email', flat=True))
        
        success = send_vacation_closure_email(
            recipients=recipient_emails,
            start_closure_day_name=DAYS_ES[start_date.weekday()],
            start_closure_day_number=start_date.day,
            end_closure_day_name=DAYS_ES[end_date.weekday()],
            end_closure_day_number=end_date.day,
            month_closure=MONTHS_ES[start_date.month - 1],
            closure_reason=options['reason'],
            reopening_day_name=DAYS_ES[reopen_date.weekday()],
            reopening_day_number=reopen_date.day,
            month_reopening=MONTHS_ES[reopen_date.month - 1]
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS(f'✅ Aviso enviado a {len(recipient_emails)} padres'))
        else:
            self.stdout.write(self.style.ERROR('❌ Error al enviar avisos'))

    def send_tax_certificate_email(self, options):
        """Envía certificados fiscales para la renta"""
        from core.email import send_tax_certificate_email, send_all_tax_certificates
        
        if not options.get('year'):
            raise CommandError('Se requiere --year para el certificado')
        
        year = options['year']
        
        # Si se especifica un destinatario, enviar solo a él
        if options.get('recipient'):
            # Buscar el padre por email
            try:
                parent = Parent.objects.get(email=options['recipient'])
            except Parent.DoesNotExist:
                raise CommandError(f'No se encontró padre con email {options["recipient"]}')
            
            self.stdout.write(f'📄 Generando certificado fiscal {year} para {parent.full_name}...')
            
            success = send_tax_certificate_email(
                parent=parent,
                year=year
            )
            
            if success:
                self.stdout.write(self.style.SUCCESS(f'✅ Certificado enviado a {parent.email}'))
            else:
                self.stdout.write(self.style.ERROR('❌ Error al enviar certificado (¿tiene pagos en ese año?)'))
        
        else:
            # Enviar a TODOS los padres con pagos en ese año
            self.stdout.write(f'📄 Generando y enviando certificados fiscales {year} a todos los padres...')
            
            results = send_all_tax_certificates(year)
            
            self.stdout.write(self.style.SUCCESS(
                f'\n📊 Resultado: {results["sent"]} enviados, '
                f'{results["skipped"]} omitidos, {results["failed"]} fallidos'
            ))

    def send_quarterly_receipt(self, options):
        """Envía recibo trimestral"""
        
        if not options.get('student_id'):
            raise CommandError('Se requiere --student-id')
        if not options.get('months'):
            raise CommandError('Se requiere --months (mes1,mes2,mes3)')
        
        try:
            student = Student.objects.get(pk=options['student_id'])
        except Student.DoesNotExist:
            raise CommandError(f'No se encontró estudiante con ID {options["student_id"]}')
        
        # Obtener padre
        parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
        if not parent:
            raise CommandError(f'El estudiante {student.full_name} no tiene padre con email')
        
        # Parsear meses
        months = options['months'].split(',')
        if len(months) != 3:
            raise CommandError('Se requieren exactamente 3 meses separados por coma')
        
        # Preparar PDF si existe
        receipt_pdf = None
        if options.get('pdf') and os.path.exists(options['pdf']):
            with open(options['pdf'], 'rb') as f:
                receipt_pdf = (
                    f'recibo_trimestre_{student.first_name}.pdf',
                    f.read(),
                    'application/pdf'
                )
        
        self.stdout.write(f'🧾 Enviando recibo trimestral de {student.full_name} a {parent.email}...')
        
        success = send_quarterly_receipt_email(
            parent_email=parent.email,
            student_name=student.full_name,
            month_1=months[0].strip(),
            month_2=months[1].strip(),
            month_3=months[2].strip(),
            receipt_pdf=receipt_pdf
        )
        
        if success:
            self.stdout.write(self.style.SUCCESS('✅ Recibo enviado'))
        else:
            self.stdout.write(self.style.ERROR('❌ Error al enviar recibo'))
