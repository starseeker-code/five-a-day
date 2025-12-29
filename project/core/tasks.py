"""
Tareas Celery para envío automático de emails
Estas tareas se pueden programar con Celery Beat para ejecución periódica

Configuración en project/celery.py para Celery Beat.

Uso manual:
    # Enviar email de bienvenida de forma asíncrona
    send_welcome_email_task.delay(parent_id=1, student_id=2, enrollment_id=3)
    
    # Ejecutar manualmente los cumpleaños de hoy
    send_birthday_emails_task.delay()
"""
from celery import shared_task
from celery.utils.log import get_task_logger
from datetime import date

logger = get_task_logger(__name__)


@shared_task(
    name='core.tasks.send_welcome_email_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_welcome_email_task(self, parent_id: int, student_id: int, enrollment_id: int):
    """
    Tarea asíncrona para enviar email de bienvenida.
    Se ejecuta cuando se crea un nuevo estudiante.
    
    Args:
        parent_id: ID del padre/tutor
        student_id: ID del estudiante
        enrollment_id: ID de la matrícula
    """
    from core.models import Parent, Student, Enrollment
    from core.email import email_service
    
    try:
        parent = Parent.objects.get(id=parent_id)
        student = Student.objects.select_related('group').get(id=student_id)
        enrollment = Enrollment.objects.select_related('enrollment_type').get(id=enrollment_id)
        
        context = {
            'parent_name': parent.full_name,
            'student_name': student.full_name,
            'group_name': student.group.group_name if student.group else None,
            'enrollment_type': enrollment.enrollment_type.display_name if enrollment.enrollment_type else None,
            'schedule_type': enrollment.get_schedule_type_display(),
            'start_date': enrollment.enrollment_period_start.strftime('%d/%m/%Y') if enrollment.enrollment_period_start else None,
        }
        
        success = email_service.send_email(
            template_name='welcome_student',
            recipients=parent.email,
            subject=f'🎓 ¡Bienvenido/a {student.full_name} a Five a Day!',
            context=context
        )
        
        if success:
            logger.info(f"✅ Email de bienvenida enviado a {parent.email} para {student.full_name}")
        else:
            logger.error(f"❌ Error al enviar email de bienvenida a {parent.email}")
            raise Exception("Fallo en el envío del email")
        
        return {'status': 'success', 'recipient': parent.email}
        
    except (Parent.DoesNotExist, Student.DoesNotExist, Enrollment.DoesNotExist) as e:
        logger.error(f"❌ No se encontró el registro: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(
    name='core.tasks.send_birthday_email_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_birthday_email_task(self, student_id: int):
    """
    Tarea asíncrona para enviar email de cumpleaños a un estudiante específico.
    
    Args:
        student_id: ID del estudiante
    """
    from core.models import Student
    from core.email import email_service
    
    try:
        student = Student.objects.prefetch_related('parents').get(id=student_id)
        
        # Obtener el primer padre con email
        parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
        
        if not parent:
            logger.warning(f"⚠️ {student.full_name} no tiene padre con email")
            return {'status': 'skipped', 'reason': 'no parent email'}
        
        success = email_service.send_email(
            template_name='happy_birthday',
            recipients=parent.email,
            subject=f'🎉 ¡Feliz Cumpleaños {student.first_name}!',
            context={'name': student.first_name}
        )
        
        if success:
            logger.info(f"🎂 Email de cumpleaños enviado a {parent.email} para {student.full_name}")
        else:
            raise Exception("Fallo en el envío del email")
        
        return {'status': 'success', 'recipient': parent.email, 'student': student.full_name}
        
    except Student.DoesNotExist:
        logger.error(f"❌ Estudiante con ID {student_id} no existe")
        return {'status': 'error', 'message': 'Student not found'}


@shared_task(name='core.tasks.send_birthday_emails_task', bind=True)
def send_birthday_emails_task(self):
    """
    Tarea programada (Celery Beat) que se ejecuta diariamente.
    Busca todos los estudiantes que cumplen años hoy y encola emails individuales.
    
    Configurada en celery.py para ejecutarse a las 8:00 AM.
    """
    from core.models import Student
    
    today = date.today()
    
    # Buscar estudiantes activos que cumplen hoy
    birthday_students = Student.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day,
        active=True
    ).values_list('id', flat=True)
    
    if not birthday_students:
        logger.info("ℹ️ No hay cumpleaños hoy")
        return {'status': 'success', 'birthdays_found': 0}
    
    logger.info(f"🎂 Encontrados {len(birthday_students)} cumpleaños hoy")
    
    # Encolar cada email como tarea separada (para mejor manejo de errores y reintentos)
    for student_id in birthday_students:
        send_birthday_email_task.delay(student_id)
    
    return {
        'status': 'success',
        'birthdays_found': len(birthday_students),
        'tasks_queued': len(birthday_students)
    }


@shared_task(name='core.tasks.send_payment_reminders', bind=True)
def send_payment_reminders(self):
    """
    Tarea semanal: Envía recordatorios de pago a padres con pagos pendientes
    Busca pagos pendientes próximos a vencer (en los próximos 7 días)
    """
    from core.models import Payment
    from core.email import email_service
    from datetime import timedelta
    
    due_date_limit = date.today() + timedelta(days=7)
    
    pending_payments = Payment.objects.filter(
        payment_status='pending',
        due_date__lte=due_date_limit,
        due_date__gte=date.today()
    ).select_related('student', 'parent')
    
    if not pending_payments.exists():
        logger.info("💳 No hay pagos pendientes próximos a vencer")
        return {'status': 'no_pending_payments', 'sent': 0}
    
    logger.info(f"💳 Enviando {pending_payments.count()} recordatorios de pago")
    
    emails_data = []
    for payment in pending_payments:
        if payment.parent and payment.parent.email:
            emails_data.append({
                'recipient': payment.parent.email,
                'subject': f'Recordatorio de Pago - {payment.student.full_name}',
                'context': {
                    'student_name': payment.student.full_name,
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


@shared_task(
    name='core.tasks.send_generic_email_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_generic_email_task(
    self,
    template_name: str,
    recipient_email: str,
    subject: str,
    context: dict = None
):
    """
    Tarea genérica para enviar cualquier tipo de email.
    Útil para emails que no tienen una tarea específica.
    
    Args:
        template_name: Nombre del template (sin .html)
        recipient_email: Email del destinatario
        subject: Asunto del email
        context: Variables para el template
    
    Uso:
        send_generic_email_task.delay(
            template_name='payment_reminder',
            recipient_email='parent@example.com',
            subject='Recordatorio de Pago',
            context={'student_name': 'Juan', 'amount': 100}
        )
    """
    from core.email import email_service
    
    logger.info(f"📧 Enviando email: {template_name} → {recipient_email}")
    
    success = email_service.send_email(
        template_name=template_name,
        recipients=recipient_email,
        subject=subject,
        context=context or {}
    )
    
    if success:
        logger.info(f"✅ Email '{subject}' enviado a {recipient_email}")
        return {'status': 'success', 'recipient': recipient_email}
    else:
        raise Exception(f"Fallo al enviar email a {recipient_email}")
