"""
Comando Django para enviar emails
Uso:
    python manage.py send_email --template happy_birthday --recipient user@example.com --subject "Feliz Cumpleaños"
    python manage.py send_email --template monthly_report --test
"""
from django.core.management.base import BaseCommand, CommandError
from core.email import email_service
from core.models import Student, Parent
from django.conf import settings
import json


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
        
        # Buscar estudiantes que cumplen hoy
        birthday_students = Student.objects.filter(
            birth_date__month=today.month,
            birth_date__day=today.day
        ).select_related('parent')
        
        if not birthday_students.exists():
            self.stdout.write(self.style.WARNING('ℹ️  No hay cumpleaños hoy'))
            return
        
        self.stdout.write(f'🎂 Encontrados {birthday_students.count()} cumpleaños hoy')
        
        sent = 0
        failed = 0
        
        for student in birthday_students:
            if not student.parent or not student.parent.email:
                self.stdout.write(self.style.WARNING(f'⚠️  {student.name}: Sin email del padre'))
                failed += 1
                continue
            
            success = email_service.send_email(
                template_name='happy_birthday',
                recipients=student.parent.email,
                subject=f'🎉 ¡Feliz Cumpleaños {student.name}!',
                context={'name': student.name}
            )
            
            if success:
                sent += 1
                self.stdout.write(f'  ✅ {student.name} → {student.parent.email}')
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {student.name} → {student.parent.email}'))
        
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
            # Obtener datos del reporte (puedes personalizar esto)
            students = parent.student_set.all()
            
            context = {
                'parent_name': parent.name,
                'students': [
                    {
                        'name': s.name,
                        'group': s.group.name if s.group else 'Sin grupo'
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
                self.stdout.write(f'  ✅ {parent.name} → {parent.email}')
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  ❌ {parent.name} → {parent.email}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n📊 Resultado: {sent} enviados, {failed} fallidos'))
