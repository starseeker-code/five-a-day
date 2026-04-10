"""
Email service for Five a Day.
Provides the core EmailService class and configuration helper.

Moved from core/email.py as part of the comms app split.
"""
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from email.mime.image import MIMEImage
from typing import List, Dict, Optional, Union
import logging
import os

logger = logging.getLogger(__name__)


def get_email_config():
    """
    Obtiene la configuracion de email desde settings/variables de entorno.
    Esta funcion asegura que siempre usamos los valores correctos del .env.
    """
    return {
        'host_user': settings.EMAIL_HOST_USER,
        'host_password': settings.EMAIL_HOST_PASSWORD,
        'from_email': settings.DEFAULT_FROM_EMAIL,
        'backend': settings.EMAIL_BACKEND,
    }


class EmailService:
    """
    Servicio generico para envio de emails con templates HTML

    Uso:
        email_service = EmailService()
        email_service.send_email(
            template_name='happy_birthday',
            recipients=['user@example.com'],
            context={'name': 'Juan'},
            subject='Feliz Cumpleanos!'
        )
    """

    # Ruta al logo de la academia (relativa a BASE_DIR)
    LOGO_PATH = 'core/static/images/logo.png'

    def __init__(self):
        self.from_email = settings.DEFAULT_FROM_EMAIL
        self.templates_path = 'emails/'

    def _get_logo_path(self) -> str:
        """Obtiene la ruta absoluta al logo de la academia"""
        return os.path.join(settings.BASE_DIR, self.LOGO_PATH)

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
        Envia un email usando un template HTML

        Args:
            template_name: Nombre del template (sin .html), ej: 'happy_birthday'
            recipients: Email o lista de emails destinatarios
            subject: Asunto del email
            context: Diccionario con variables para el template
            cc: Lista de emails en copia
            bcc: Lista de emails en copia oculta
            fail_silently: Si True, no lanza excepciones en caso de error
            attachments: Lista de tuplas (filename, content, mimetype)
            inline_images: Dict de {content_id: file_path} para imagenes inline
                           En el template usar: <img src="cid:content_id">

        Returns:
            True si se envio correctamente, False en caso contrario
        """
        try:
            # Convertir recipient a lista si es string
            if isinstance(recipients, str):
                recipients = [recipients]

            # Preparar contexto
            if context is None:
                context = {}

            # Anadir variables globales al contexto
            context.setdefault('year', 2025)
            context.setdefault('site_name', 'Five a Day')

            # Renderizar template HTML
            template_path = f'{self.templates_path}{template_name}.html'
            html_content = render_to_string(template_path, context)

            # Crear version texto plano (opcional, para clientes sin HTML)
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

            # Anadir imagenes inline si existen
            if inline_images:
                email.mixed_subtype = 'related'
                for content_id, image_path in inline_images.items():
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as img_file:
                            img = MIMEImage(img_file.read())
                            img.add_header('Content-ID', f'<{content_id}>')
                            img.add_header('Content-Disposition', 'inline', filename=os.path.basename(image_path))
                            email.attach(img)

            # Anadir adjuntos si existen
            if attachments:
                for filename, content, mimetype in attachments:
                    email.attach(filename, content, mimetype)

            # Enviar email
            email.send(fail_silently=fail_silently)

            logger.info(f"Email '{subject}' enviado a {len(recipients)} destinatario(s)")
            return True

        except Exception as e:
            logger.error(f"Error enviando email '{subject}': {str(e)}")
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
        Envia multiples emails usando el mismo template

        Args:
            template_name: Nombre del template
            emails_data: Lista de diccionarios con {recipient, subject, context}
            fail_silently: Si True, continua aunque falle alguno

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

        logger.info(f"Envio masivo completado: {results['sent']} enviados, {results['failed']} fallidos")
        return results


# Instancia global del servicio
email_service = EmailService()
