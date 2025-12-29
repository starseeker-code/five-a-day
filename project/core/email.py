"""
Sistema genérico de envío de emails para Five a Day
Soporta múltiples templates y puede ser usado desde comandos Django o Celery tasks
"""
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
from typing import List, Dict, Optional, Union
import logging
import os

logger = logging.getLogger(__name__)


def get_email_config():
    """
    Obtiene la configuración de email desde settings/variables de entorno.
    Esta función asegura que siempre usamos los valores correctos del .env.
    """
    return {
        'host_user': settings.EMAIL_HOST_USER,
        'host_password': settings.EMAIL_HOST_PASSWORD,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'backend': settings.EMAIL_BACKEND,
    }


class EmailService:
    """
    Servicio genérico para envío de emails con templates HTML
    
    Uso:
        email_service = EmailService()
        email_service.send_email(
            template_name='happy_birthday',
            recipients=['user@example.com'],
            context={'name': 'Juan'},
            subject='¡Feliz Cumpleaños!'
        )
    """
    
    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.templates_path = 'emails/'
    
    def send_email(
        self,
        template_name: str,
        recipients: Union[str, List[str]],
        subject: str,
        context: Optional[Dict] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None,
        fail_silently: bool = False,
        attachments: Optional[List] = None,
        inline_images: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Envía un email usando un template HTML
        
        Args:
            template_name: Nombre del template (sin .html), ej: 'happy_birthday'
            recipients: Email o lista de emails destinatarios
            subject: Asunto del email
            context: Diccionario con variables para el template
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta
            fail_silently: Si True, no lanza excepciones en caso de error
            attachments: Lista de tuplas (filename, content, mimetype)
            inline_images: Dict de {content_id: file_path} para imágenes inline
                           En el template usar: <img src="cid:content_id">
        
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        try:
            # Convertir recipient a lista si es string
            if isinstance(recipients, str):
                recipients = [recipients]
            
            # Preparar contexto
            if context is None:
                context = {}
            
            # Añadir variables globales al contexto
            context.setdefault('year', 2025)
            context.setdefault('site_name', 'Five a Day')
            
            # Renderizar template HTML
            template_path = f'{self.templates_path}{template_name}.html'
            html_content = render_to_string(template_path, context)
            
            # Crear versión texto plano (opcional, para clientes sin HTML)
            text_content = f"{subject}\n\nVer este mensaje en un cliente compatible con HTML."
            
            # Crear email con alternativas (texto y HTML)
            email = EmailMultiAlternatives(
                subject=subject,
                body=text_content,
                from_email=self.from_email,
                to=recipients,
                cc=cc,
                bcc=bcc
            )
            email.attach_alternative(html_content, "text/html")
            
            # Añadir imágenes inline si existen
            if inline_images:
                email.mixed_subtype = 'related'
                for content_id, image_path in inline_images.items():
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as img_file:
                            img = MIMEImage(img_file.read())
                            img.add_header('Content-ID', f'<{content_id}>')
                            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                            email.attach(img)
            
            # Añadir adjuntos si existen
            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)
            
            # Enviar email
            email.send(fail_silently=fail_silently)
            
            logger.info(f"✅ Email '{subject}' enviado a {len(recipients)} destinatario(s)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error enviando email '{subject}': {str(e)}")
            if not fail_silently:
                raise
            return False
    
    def send_bulk_emails(
        self,
        template_name: str,
        emails_data: List[Dict],
        fail_silently: bool = True
    ) -> Dict[str, int]:
        """
        Envía múltiples emails usando el mismo template
        
        Args:
            template_name: Nombre del template
            emails_data: Lista de diccionarios con {recipient, subject, context}
            fail_silently: Si True, continúa aunque falle alguno
        
        Returns:
            Diccionario con {sent: N, failed: N}
        """
        results = {'sent': 0, 'failed': 0}
        
        for email_data in emails_data:
            success = self.send_email(
                template_name=template_name,
                recipients=email_data['recipient'],
                subject=email_data.get('subject', 'Five a Day'),
                context=email_data.get('context', {}),
                fail_silently=fail_silently
            )
            
            if success:
                results['sent'] += 1
            else:
                results['failed'] += 1
        
        logger.info(f"📧 Envío masivo completado: {results['sent']} enviados, {results['failed']} fallidos")
        return results


# Instancia global del servicio
email_service = EmailService()


# Funciones de conveniencia para emails específicos
def send_birthday_email(recipient: str, name: str) -> bool:
    """Envía email de cumpleaños"""
    return email_service.send_email(
        template_name='happy_birthday',
        recipients=recipient,
        subject=f'🎉 ¡Feliz Cumpleaños {name}!',
        context={'name': name}
    )


def send_payment_reminder(recipient: str, student_name: str, amount: float, due_date: str) -> bool:
    """Envía recordatorio de pago pendiente"""
    return email_service.send_email(
        template_name='payment_reminder',
        recipients=recipient,
        subject=f'Recordatorio de Pago - {student_name}',
        context={
            'student_name': student_name,
            'amount': amount,
            'due_date': due_date
        }
    )


def send_monthly_report(recipient: str, report_data: Dict) -> bool:
    """Envía reporte mensual"""
    return email_service.send_email(
        template_name='monthly_report',
        recipients=recipient,
        subject='📊 Reporte Mensual - Five a Day',
        context=report_data
    )


def send_welcome_email(
    parent_email: str,
    parent_name: str,
    student_name: str,
    group_name: str = None,
    enrollment_type: str = None,
    schedule_type: str = None,
    start_date: str = None
) -> bool:
    """
    Envía email de bienvenida cuando se matricula un nuevo estudiante.
    
    Args:
        parent_email: Email del padre/tutor
        parent_name: Nombre del padre/tutor
        student_name: Nombre del estudiante
        group_name: Nombre del grupo asignado
        enrollment_type: Tipo de matrícula
        schedule_type: Tipo de horario
        start_date: Fecha de inicio del período
    
    Returns:
        True si se envió correctamente
    """
    return email_service.send_email(
        template_name='welcome_student',
        recipients=parent_email,
        subject=f'🎓 ¡Bienvenido/a {student_name} a Five a Day!',
        context={
            'parent_name': parent_name,
            'student_name': student_name,
            'group_name': group_name,
            'enrollment_type': enrollment_type,
            'schedule_type': schedule_type,
            'start_date': start_date,
        },
        fail_silently=True  # No queremos que falle la creación si el email falla
    )
