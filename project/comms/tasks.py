"""
Celery tasks for automated email sending.
These tasks can be scheduled with Celery Beat for periodic execution.

Moved from core/tasks.py as part of the comms app split.

Usage:
    # Send welcome email asynchronously
    send_welcome_email_task.delay(parent_id=1, student_id=2, enrollment_id=3)

    # Manually trigger today's birthday emails
    send_birthday_emails_task.delay()
"""

from datetime import date

from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    name="comms.tasks.send_welcome_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def send_welcome_email_task(self, parent_id: int, student_id: int, enrollment_id: int):
    """
    Async task to send a welcome email.
    Triggered when a new student is created.

    Args:
        parent_id: ID of the parent/guardian
        student_id: ID of the student
        enrollment_id: ID of the enrollment
    """
    from comms.services.email_service import email_service
    from students.models import Enrollment, Parent, Student

    try:
        student = Student.objects.select_related("group").get(id=student_id)
        enrollment = Enrollment.objects.select_related("enrollment_type").get(id=enrollment_id)

        # For adult students, email goes to the student; for children, to the parent
        if parent_id:
            parent = Parent.objects.get(id=parent_id)
            recipient_email = parent.email
            recipient_name = parent.full_name
        else:
            recipient_email = student.email
            recipient_name = student.full_name

        if not recipient_email:
            logger.warning("No email address for welcome email (student_id=%d)", student_id)
            return {"status": "skipped", "message": "No email address"}

        context = {
            "parent_name": recipient_name,
            "student_name": student.full_name,
            "group_name": student.group.group_name if student.group else None,
            "enrollment_type": enrollment.enrollment_type.display_name if enrollment.enrollment_type else None,
            "schedule_type": enrollment.get_schedule_type_display(),
            "start_date": enrollment.enrollment_date.strftime("%d/%m/%Y") if enrollment.enrollment_date else None,
        }

        success = email_service.send_email(
            template_name="welcome_student",
            recipients=recipient_email,
            subject=f"🎓 ¡Bienvenido/a {student.full_name} a Five a Day!",
            context=context,
        )

        if success:
            logger.info("Welcome email sent for student_id=%d", student_id)
        else:
            logger.error("Failed to send welcome email for student_id=%d", student_id)
            raise Exception("Fallo en el envio del email")

        return {"status": "success", "recipient": recipient_email}

    except (Parent.DoesNotExist, Student.DoesNotExist, Enrollment.DoesNotExist) as e:
        logger.error(
            "Record not found: parent_id=%s student_id=%s enrollment_id=%s", parent_id, student_id, enrollment_id
        )
        return {"status": "error", "message": str(e)}


@shared_task(
    name="comms.tasks.send_birthday_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def send_birthday_email_task(self, student_id: int):
    """
    Async task to send a birthday email to a specific student.

    Args:
        student_id: ID of the student
    """
    from comms.services.email_service import email_service
    from students.models import Student

    try:
        student = Student.objects.prefetch_related("parents").get(id=student_id)

        # Get the first parent with an email
        parent = student.parents.exclude(email="").exclude(email__isnull=True).first()

        if not parent:
            logger.warning("Student id=%d has no parent with email", student_id)
            return {"status": "skipped", "reason": "no parent email"}

        success = email_service.send_email(
            template_name="happy_birthday",
            recipients=parent.email,
            subject=f"🎉 ¡Feliz Cumpleaños {student.first_name}!",
            context={"name": student.first_name},
        )

        if success:
            logger.info("Birthday email sent for student_id=%d", student_id)
        else:
            raise Exception("Fallo en el envio del email")

        return {"status": "success", "recipient": parent.email, "student": student.full_name}

    except Student.DoesNotExist:
        logger.error("Student not found: id=%d", student_id)
        return {"status": "error", "message": "Student not found"}


@shared_task(name="comms.tasks.send_birthday_emails_task", bind=True)
def send_birthday_emails_task(self):
    """
    Scheduled task (Celery Beat) that runs daily.
    Finds all students with a birthday today and queues individual emails.

    Configured in celery.py to run at 8:00 AM.
    """
    from students.models import Student

    today = date.today()

    # Find active students with a birthday today
    birthday_students = Student.objects.filter(
        birth_date__month=today.month, birth_date__day=today.day, active=True
    ).values_list("id", flat=True)

    if not birthday_students:
        logger.info("No hay cumpleanos hoy")
        return {"status": "success", "birthdays_found": 0}

    logger.info(f"Encontrados {len(birthday_students)} cumpleanos hoy")

    # Queue each email as a separate task (for better error handling and retries)
    for student_id in birthday_students:
        send_birthday_email_task.delay(student_id)

    return {"status": "success", "birthdays_found": len(birthday_students), "tasks_queued": len(birthday_students)}


@shared_task(name="comms.tasks.send_payment_reminders", bind=True)
def send_payment_reminders(self):
    """
    Weekly task: Send payment reminders to parents with pending payments.
    Looks for pending payments due within the next 7 days.
    """
    from datetime import timedelta

    from billing.models import Payment
    from comms.services.email_service import email_service

    due_date_limit = date.today() + timedelta(days=7)

    pending_payments = Payment.objects.filter(
        payment_status="pending", due_date__lte=due_date_limit, due_date__gte=date.today()
    ).select_related("student", "parent")

    if not pending_payments.exists():
        logger.info("No hay pagos pendientes proximos a vencer")
        return {"status": "no_pending_payments", "sent": 0}

    logger.info(f"Enviando {pending_payments.count()} recordatorios de pago")

    emails_data = []
    for payment in pending_payments:
        if payment.parent and payment.parent.email:
            emails_data.append(
                {
                    "recipient": payment.parent.email,
                    "subject": f"Recordatorio de Pago - {payment.student.full_name}",
                    "context": {
                        "student_name": payment.student.full_name,
                        "amount": float(payment.amount),
                        "due_date": payment.due_date.strftime("%d/%m/%Y"),
                    },
                }
            )

    results = email_service.send_bulk_emails(
        template_name="payment_reminder", emails_data=emails_data, fail_silently=True
    )

    logger.info(f"Recordatorios enviados: {results['sent']} exitosos, {results['failed']} fallidos")
    return results


@shared_task(
    name="comms.tasks.send_generic_email_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(Exception,),
)
def send_generic_email_task(self, template_name: str, recipient_email: str, subject: str, context: dict = None):
    """
    Generic task to send any type of email.
    Useful for emails that don't have a specific task.

    Args:
        template_name: Template name (without .html)
        recipient_email: Recipient email address
        subject: Email subject
        context: Template variables

    Usage:
        send_generic_email_task.delay(
            template_name='payment_reminder',
            recipient_email='parent@example.com',
            subject='Recordatorio de Pago',
            context={'student_name': 'Juan', 'amount': 100}
        )
    """
    from comms.services.email_service import email_service

    logger.info("Sending email: template=%s", template_name)

    success = email_service.send_email(
        template_name=template_name, recipients=recipient_email, subject=subject, context=context or {}
    )

    if success:
        logger.info("Email sent: template=%s", template_name)
        return {"status": "success"}
    else:
        raise Exception(f"Failed to send email: template={template_name}")


# ============================================================================
# TASK: Enrollment Confirmation (matricula_nino.html)
# ============================================================================


@shared_task(
    name="comms.tasks.send_enrollment_confirmation_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_enrollment_confirmation_task(self, enrollment_id: int, attachments_paths: list = None):
    """
    Send enrollment confirmation email with attached documents.

    Args:
        enrollment_id: ID of the enrollment
        attachments_paths: List of paths to attached PDFs (optional)
    """
    import os

    from comms.services.email_functions import send_enrollment_confirmation_email
    from students.models import Enrollment

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

    try:
        enrollment = (
            Enrollment.objects.select_related("student", "student__group")
            .prefetch_related("student__parents")
            .get(id=enrollment_id)
        )

        student = enrollment.student
        parent = student.parents.exclude(email="").exclude(email__isnull=True).first()

        if not parent:
            logger.error("No parent with email for enrollment_id=%d", enrollment_id)
            return {"status": "error", "message": "No parent email"}

        academic_year = enrollment.academic_year

        # Prepare attachments
        attachments = []
        if attachments_paths:
            for path in attachments_paths:
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        attachments.append((os.path.basename(path), f.read(), "application/pdf"))

        success = send_enrollment_confirmation_email(
            parent_email=parent.email,
            student_name=student.full_name,
            gender=student.gender,
            academic_year=academic_year,
            month=MONTHS_ES[enrollment.enrollment_date.month - 1],
            attachments=attachments if attachments else None,
        )

        if success:
            logger.info("Enrollment confirmation sent for enrollment_id=%d", enrollment_id)
            return {"status": "success", "recipient": parent.email}
        else:
            raise Exception("Fallo en envio de confirmacion de matricula")

    except Enrollment.DoesNotExist:
        logger.error("Enrollment not found: id=%d", enrollment_id)
        return {"status": "error", "message": "Enrollment not found"}
