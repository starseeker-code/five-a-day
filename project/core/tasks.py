"""
Tareas Celery para envío automático de emails
Estas tareas se pueden programar con Celery Beat para ejecución periódica

Configuración en celery.py:
    from celery.schedules import crontab
    
    app.conf.beat_schedule = {
        'send-birthday-emails-daily': {
            'task': 'core.tasks.send_daily_birthday_emails',
            'schedule': crontab(hour=9, minute=0),  # Todos los días a las 9:00
        },
        'send-monthly-reports': {
            'task': 'core.tasks.send_monthly_reports_task',
            'schedule': crontab(day_of_month=1, hour=10, minute=0),  # Día 1 del mes a las 10:00
        },
    }
"""
from celery import shared_task
from core.email import email_service
from core.models import Student, Parent
from datetime import date
import logging

logger = logging.getLogger(__name__)


@shared_task(name='core.tasks.send_daily_birthday_emails')
def send_daily_birthday_emails():
    """
    Tarea diaria: Envía emails de cumpleaños a estudiantes que cumplen hoy
    Se ejecuta automáticamente cada día a las 9:00 AM
    """
    today = date.today()
    
    # Buscar estudiantes con cumpleaños hoy
    birthday_students = Student.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day
    ).select_related('parent')
    
    if not birthday_students.exists():
        logger.info("📅 No hay cumpleaños hoy")
        return {'status': 'no_birthdays', 'sent': 0}
    
    logger.info(f"🎂 Encontrados {birthday_students.count()} cumpleaños hoy")
    
    emails_data = []
    for student in birthday_students:
        if student.parent and student.parent.email:
            emails_data.append({
                'recipient': student.parent.email,
                'subject': f'🎉 ¡Feliz Cumpleaños {student.name}!',
                'context': {'name': student.name}
            })
    
    results = email_service.send_bulk_emails(
        template_name='happy_birthday',
        emails_data=emails_data,
        fail_silently=True
    )
    
    logger.info(f"✅ Cumpleaños enviados: {results['sent']} exitosos, {results['failed']} fallidos")
    return results


@shared_task(name='core.tasks.send_monthly_reports_task')
def send_monthly_reports_task():
    """
    Tarea mensual: Envía reportes mensuales a todos los padres
    Se ejecuta el día 1 de cada mes a las 10:00 AM
    """
    parents = Parent.objects.filter(email__isnull=False).exclude(email='').prefetch_related('student_set__group')
    
    if not parents.exists():
        logger.info("📊 No hay padres con email para reportes")
        return {'status': 'no_parents', 'sent': 0}
    
    logger.info(f"📊 Enviando reportes mensuales a {parents.count()} padres")
    
    emails_data = []
    for parent in parents:
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
            'total_students': students.count(),
            'month': date.today().strftime('%B'),
            'year': date.today().year
        }
        
        emails_data.append({
            'recipient': parent.email,
            'subject': '📊 Reporte Mensual - Five a Day',
            'context': context
        })
    
    results = email_service.send_bulk_emails(
        template_name='monthly_report',
        emails_data=emails_data,
        fail_silently=True
    )
    
    logger.info(f"✅ Reportes enviados: {results['sent']} exitosos, {results['failed']} fallidos")
    return results


@shared_task(name='core.tasks.send_payment_reminders')
def send_payment_reminders():
    """
    Tarea semanal: Envía recordatorios de pago a padres con pagos pendientes
    Configura en celery beat_schedule según necesites
    """
    from core.models import Payment
    from datetime import timedelta
    
    # Buscar pagos pendientes próximos a vencer (ej: en los próximos 7 días)
    due_date_limit = date.today() + timedelta(days=7)
    
    pending_payments = Payment.objects.filter(
        payment_status='pending',
        due_date__lte=due_date_limit,
        due_date__gte=date.today()
    ).select_related('student__parent')
    
    if not pending_payments.exists():
        logger.info("💳 No hay pagos pendientes próximos a vencer")
        return {'status': 'no_pending_payments', 'sent': 0}
    
    logger.info(f"💳 Enviando {pending_payments.count()} recordatorios de pago")
    
    emails_data = []
    for payment in pending_payments:
        parent = payment.student.parent
        if parent and parent.email:
            emails_data.append({
                'recipient': parent.email,
                'subject': f'Recordatorio de Pago - {payment.student.name}',
                'context': {
                    'student_name': payment.student.name,
                    'amount': float(payment.amount),
                    'due_date': payment.due_date.strftime('%d/%m/%Y')
                }
            })
    
    results = email_service.send_bulk_emails(
        template_name='payment_reminder',
        emails_data=emails_data,
        fail_silently=True
    )
    
    logger.info(f"✅ Recordatorios enviados: {results['sent']} exitosos, {results['failed']} fallidos")
    return results


@shared_task(name='core.tasks.send_custom_email')
def send_custom_email(template_name, recipient, subject, context):
    """
    Tarea genérica: Envía un email personalizado
    Útil para emails bajo demanda desde otras partes de la aplicación
    
    Uso:
        send_custom_email.delay(
            template_name='payment_reminder',
            recipient='parent@example.com',
            subject='Recordatorio de Pago',
            context={'student_name': 'Juan', 'amount': 100}
        )
    """
    logger.info(f"📧 Enviando email personalizado: {template_name} → {recipient}")
    
    success = email_service.send_email(
        template_name=template_name,
        recipients=recipient,
        subject=subject,
        context=context
    )
    
    return {'status': 'sent' if success else 'failed', 'recipient': recipient}
