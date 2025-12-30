"""
Sistema genérico de envío de emails para Five a Day
Soporta múltiples templates y puede ser usado desde comandos Django o Celery tasks

================================================================================
CATÁLOGO DE TEMPLATES DE EMAIL
================================================================================

1. emails/welcome_student.html
   - Propósito: Bienvenida a nuevo estudiante (niño)
   - Cuándo se envía: Automáticamente al crear un nuevo estudiante
   - Destinatario: Email del padre/tutor
   - Variables: parent_name, student_name, group_name, enrollment_type, 
                schedule_type, start_date
   - Implementado en: StudentCreateView (views.py)

2. emails/happy_birthday.html
   - Propósito: Felicitación de cumpleaños
   - Cuándo se envía: Diariamente a las 8:00 AM (hora España) via Cron Job
   - Destinatario: Email del padre del estudiante que cumple años
   - Variables: name
   - Imágenes inline: logo, birthday_image
   - Implementado en: Render Cron Job + send_email command

3. emails/matricula_niño.html
   - Propósito: Confirmación de matrícula para niños
   - Cuándo se envía: Al confirmar matrícula de un niño (manual o automático)
   - Destinatario: Email del padre/tutor
   - Variables: student, genero ("m"/"f"), academic_year, month
   - Adjuntos: PDF informativo grupo/horario, normativa, recibos matrícula
   - Estado: Template listo, falta implementar lógica

4. emails/fun_friday.html
   - Propósito: Invitación a eventos Fun Friday (actividades de viernes)
   - Cuándo se envía: Cada semana antes del viernes (manual)
   - Destinatario: Todos los padres de estudiantes elegibles por edad
   - Variables: day_name, day_number, month, start_time, end_time,
                activity_description, meeting_point, minimum_age, maximum_age
   - Imágenes inline: logo, event_image (opcional)
   - Estado: Template listo, falta implementar lógica

5. emails/recordatorio_pago_mensual_trimestral.html
   - Propósito: Recordatorio de pago mensual/trimestral
   - Cuándo se envía: Inicio de cada mes (días 1-5)
   - Destinatario: Todos los padres con pagos pendientes
   - Variables: payment_start_day_name, payment_start_day_number,
                payment_end_day_name, payment_end_day_number, month,
                iban_number, reduced_price_cheque_idioma, telephone_number_bizum
   - Adjuntos: PDF con tarifas, instrucciones de pago
   - Estado: Template listo, falta implementar lógica

6. emails/recibo_trimestre_niño.html
   - Propósito: Envío de recibo trimestral para niños
   - Cuándo se envía: Al generar recibo trimestral
   - Destinatario: Email del padre/tutor
   - Variables: month_1, month_2, month_3, student_name
   - Adjuntos: Recibo PDF
   - Estado: Template listo, falta implementar lógica

7. emails/recordatorio_cierre_vacaciones.html
   - Propósito: Aviso de cierre por vacaciones
   - Cuándo se envía: Antes de cada período vacacional (manual)
   - Destinatario: Todos los padres
   - Variables: start_closure_day_name, start_closure_day_number,
                end_closure_day_name, end_closure_day_number, month_closure,
                closure_reason, reopening_day_name, reopening_day_number,
                month_reopening
   - Estado: Template listo, falta implementar lógica

8. emails/certificado_renta.html
   - Propósito: Envío de certificado para declaración de la renta
   - Cuándo se envía: Una vez al año (Abril aproximadamente)
   - Destinatario: Padres que lo soliciten
   - Variables: year
   - Adjuntos: Certificado PDF
   - Estado: Template listo, falta implementar lógica

9. emails/monthly_report.html
   - Propósito: Reporte mensual de actividad
   - Cuándo se envía: Fin de cada mes (automático)
   - Destinatario: Padres
   - Variables: month, year, parent_name, students (lista), total_students
   - Estado: Template listo, falta implementar lógica

📧 TEMPLATES PARA ADULTOS (NO IMPLEMENTAR AÚN):
--------------------------------------------------------------------------------

10. emails/matricula_adulto.html
    - Propósito: Confirmación de matrícula para adultos
    - Cuándo se envía: Al confirmar matrícula de un adulto
    - Destinatario: Email del adulto matriculado
    - Variables: genero ("m"/"f"), academic_year, month
    - Adjuntos: Recibos matrícula, normativa
    - Estado: Template listo, lógica de adultos no implementada

11. emails/recibo_adulto.html
    - Propósito: Envío de recibo mensual para adultos
    - Cuándo se envía: Al generar recibo mensual de adulto
    - Destinatario: Email del adulto
    - Variables: month
    - Adjuntos: Recibo PDF
    - Estado: Template listo, lógica de adultos no implementada

================================================================================
NOTAS TÉCNICAS:
- Todos los templates extienden de 'emails/base_email.html'
- El logo se incluye como imagen inline con cid:logo
- Las imágenes adicionales se pasan via inline_images parameter
- Path del logo: static/images/logo.png
================================================================================
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
            
            # Siempre incluir el logo de la academia
            logo_path = self._get_logo_path()
            if inline_images is None:
                inline_images = {}
            if 'logo' not in inline_images and os.path.exists(logo_path):
                inline_images['logo'] = logo_path
            
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


# ============================================================================
# 3. MATRÍCULA NIÑO - Confirmación de matrícula
# ============================================================================

def send_enrollment_confirmation_email(
    parent_email: str,
    student_name: str,
    gender: str,
    academic_year: str,
    month: str,
    attachments: Optional[List] = None
) -> bool:
    """
    Envía email de confirmación de matrícula para niños.
    
    Args:
        parent_email: Email del padre/tutor
        student_name: Nombre del estudiante
        gender: Género del estudiante ("m" o "f")
        academic_year: Año académico (ej: "2024-2025")
        month: Mes de inicio
        attachments: Lista de tuplas (filename, content, mimetype) con PDFs adjuntos
                    - PDF informativo grupo/horario
                    - Normativa de la academia
                    - Recibos de matrícula
    
    Returns:
        True si se envió correctamente
    """
    return email_service.send_email(
        template_name='matricula_niño',
        recipients=parent_email,
        subject=f'🎉 Confirmación de Matrícula - {student_name}',
        context={
            'student': student_name,
            'genero': gender,
            'academic_year': academic_year,
            'month': month,
        },
        attachments=attachments,
        fail_silently=True
    )


# ============================================================================
# 4. FUN FRIDAY - Invitación a eventos
# ============================================================================

def send_fun_friday_email(
    recipients: Union[str, List[str]],
    day_name: str,
    day_number: int,
    month: str,
    start_time: str,
    end_time: str,
    activity_description: str,
    minimum_age: int,
    maximum_age: int,
    meeting_point: str = None,
    event_image_path: str = None
) -> bool:
    """
    Envía invitación a evento Fun Friday.
    
    Args:
        recipients: Email(s) de los padres
        day_name: Nombre del día (ej: "viernes")
        day_number: Número del día
        month: Nombre del mes
        start_time: Hora de inicio (ej: "17:00")
        end_time: Hora de fin (ej: "18:30")
        activity_description: Descripción de la actividad
        minimum_age: Edad mínima
        maximum_age: Edad máxima
        meeting_point: Punto de encuentro (opcional)
        event_image_path: Ruta a imagen del evento (opcional)
    
    Returns:
        True si se envió correctamente
    """
    inline_images = {}
    if event_image_path and os.path.exists(event_image_path):
        inline_images['event_image'] = event_image_path
    
    return email_service.send_email(
        template_name='fun_friday',
        recipients=recipients,
        subject=f'🎉 Fun Friday - {day_name.capitalize()} {day_number} de {month}',
        context={
            'day_name': day_name,
            'day_number': day_number,
            'month': month,
            'start_time': start_time,
            'end_time': end_time,
            'activity_description': activity_description,
            'meeting_point': meeting_point,
            'minimum_age': minimum_age,
            'maximum_age': maximum_age,
        },
        inline_images=inline_images if inline_images else None,
        fail_silently=True
    )


# ============================================================================
# 5. RECORDATORIO DE PAGO - Mensual/Trimestral
# ============================================================================

def send_payment_reminder_email(
    recipients: Union[str, List[str]],
    payment_start_day_name: str,
    payment_start_day_number: int,
    payment_end_day_name: str,
    payment_end_day_number: int,
    month: str,
    iban_number: str,
    reduced_price_cheque_idioma: str,
    telephone_number_bizum: str,
    attachments: Optional[List] = None
) -> bool:
    """
    Envía recordatorio de pago mensual/trimestral.
    
    Args:
        recipients: Email(s) de los padres
        payment_start_day_name: Nombre del día inicio de pago
        payment_start_day_number: Número del día inicio
        payment_end_day_name: Nombre del día fin de pago
        payment_end_day_number: Número del día fin
        month: Mes del pago
        iban_number: Número IBAN para transferencias
        reduced_price_cheque_idioma: Precio reducido con cheque idioma
        telephone_number_bizum: Teléfono para Bizum
        attachments: Lista de PDFs (tarifas, instrucciones)
    
    Returns:
        True si se envió correctamente
    """
    return email_service.send_email(
        template_name='recordatorio_pago_mensual_trimestral',
        recipients=recipients,
        subject=f'💳 Recordatorio de Pago - {month}',
        context={
            'payment_start_day_name': payment_start_day_name,
            'payment_start_day_number': payment_start_day_number,
            'payment_end_day_name': payment_end_day_name,
            'payment_end_day_number': payment_end_day_number,
            'month': month,
            'iban_number': iban_number,
            'reduced_price_cheque_idioma': reduced_price_cheque_idioma,
            'telephone_number_bizum': telephone_number_bizum,
        },
        attachments=attachments,
        fail_silently=True
    )


# ============================================================================
# 6. RECIBO TRIMESTRAL NIÑO
# ============================================================================

def send_quarterly_receipt_email(
    parent_email: str,
    student_name: str,
    month_1: str,
    month_2: str,
    month_3: str,
    receipt_pdf: tuple = None
) -> bool:
    """
    Envía recibo trimestral para niños.
    
    Args:
        parent_email: Email del padre/tutor
        student_name: Nombre del estudiante
        month_1: Primer mes del trimestre
        month_2: Segundo mes del trimestre
        month_3: Tercer mes del trimestre
        receipt_pdf: Tupla (filename, content, mimetype) con el recibo PDF
    
    Returns:
        True si se envió correctamente
    """
    attachments = [receipt_pdf] if receipt_pdf else None
    
    return email_service.send_email(
        template_name='recibo_trimestre_niño',
        recipients=parent_email,
        subject=f'🧾 Recibo Trimestral - {student_name}',
        context={
            'student_name': student_name,
            'month_1': month_1,
            'month_2': month_2,
            'month_3': month_3,
        },
        attachments=attachments,
        fail_silently=True
    )


# ============================================================================
# 7. RECORDATORIO CIERRE VACACIONES
# ============================================================================

def send_vacation_closure_email(
    recipients: Union[str, List[str]],
    start_closure_day_name: str,
    start_closure_day_number: int,
    end_closure_day_name: str,
    end_closure_day_number: int,
    month_closure: str,
    closure_reason: str,
    reopening_day_name: str,
    reopening_day_number: int,
    month_reopening: str
) -> bool:
    """
    Envía aviso de cierre por vacaciones.
    
    Args:
        recipients: Email(s) de los padres
        start_closure_day_name: Nombre del día de inicio de cierre
        start_closure_day_number: Número del día de inicio
        end_closure_day_name: Nombre del día de fin de cierre
        end_closure_day_number: Número del día de fin
        month_closure: Mes del cierre
        closure_reason: Motivo del cierre (ej: "Navidad", "Semana Santa")
        reopening_day_name: Nombre del día de reapertura
        reopening_day_number: Número del día de reapertura
        month_reopening: Mes de reapertura
    
    Returns:
        True si se envió correctamente
    """
    return email_service.send_email(
        template_name='recordatorio_cierre_vacaciones',
        recipients=recipients,
        subject=f'🏖️ Cierre por {closure_reason} - Five a Day',
        context={
            'start_closure_day_name': start_closure_day_name,
            'start_closure_day_number': start_closure_day_number,
            'end_closure_day_name': end_closure_day_name,
            'end_closure_day_number': end_closure_day_number,
            'month_closure': month_closure,
            'closure_reason': closure_reason,
            'reopening_day_name': reopening_day_name,
            'reopening_day_number': reopening_day_number,
            'month_reopening': month_reopening,
        },
        fail_silently=True
    )


# ============================================================================
# 8. CERTIFICADO RENTA - Información fiscal anual
# ============================================================================

def generate_tax_certificate_pdf(parent, year: int) -> bytes:
    """
    Genera un PDF con el certificado fiscal para la declaración de la renta.
    Incluye todos los pagos realizados por el padre durante el año.
    
    Args:
        parent: Instancia del modelo Parent
        year: Año fiscal
    
    Returns:
        Bytes del PDF generado
    """
    from io import BytesIO
    from django.template.loader import render_to_string
    from core.models import Payment
    from decimal import Decimal
    
    # Obtener todos los pagos completados del padre en ese año
    payments = Payment.objects.filter(
        parent=parent,
        payment_status='completed',
        payment_date__year=year
    ).select_related('student').order_by('payment_date')
    
    # Agrupar pagos por estudiante
    students_data = {}
    total_year = Decimal('0.00')
    
    for payment in payments:
        student_name = payment.student.full_name
        if student_name not in students_data:
            students_data[student_name] = {
                'payments': [],
                'total': Decimal('0.00')
            }
        
        students_data[student_name]['payments'].append({
            'date': payment.payment_date,
            'concept': payment.concept,
            'amount': payment.amount,
            'payment_type': payment.get_payment_type_display(),
        })
        students_data[student_name]['total'] += payment.amount
        total_year += payment.amount
    
    # Generar HTML del certificado
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; font-size: 12px; }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #4F46E5; margin-bottom: 5px; }}
            .header p {{ color: #666; }}
            .info-box {{ background: #f5f5f5; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background: #4F46E5; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px; border-bottom: 1px solid #ddd; }}
            .total-row {{ font-weight: bold; background: #e8e8e8; }}
            .student-section {{ margin: 25px 0; }}
            .student-name {{ color: #4F46E5; font-size: 14px; font-weight: bold; margin-bottom: 10px; }}
            .grand-total {{ font-size: 16px; text-align: right; margin-top: 30px; padding: 15px; background: #4F46E5; color: white; }}
            .footer {{ margin-top: 40px; font-size: 10px; color: #666; text-align: center; }}
            .legal {{ margin-top: 30px; font-size: 9px; color: #888; border-top: 1px solid #ddd; padding-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>Five a Day English Academy</h1>
            <p>C/Hermanos Jiménez 25 - 02004 Albacete</p>
            <p>CIF: XXXXXXXXX | Tel: 967 049 096</p>
        </div>
        
        <h2 style="text-align: center;">CERTIFICADO FISCAL - AÑO {year}</h2>
        
        <div class="info-box">
            <p><strong>Titular:</strong> {parent.full_name}</p>
            <p><strong>DNI:</strong> {parent.dni}</p>
            <p><strong>Período:</strong> 01/01/{year} - 31/12/{year}</p>
        </div>
        
        <p>Five a Day English Academy certifica que durante el año <strong>{year}</strong> 
        se han recibido los siguientes pagos en concepto de servicios educativos:</p>
    """
    
    for student_name, data in students_data.items():
        html_content += f"""
        <div class="student-section">
            <p class="student-name">📚 Estudiante: {student_name}</p>
            <table>
                <tr>
                    <th>Fecha</th>
                    <th>Concepto</th>
                    <th>Tipo</th>
                    <th style="text-align: right;">Importe</th>
                </tr>
        """
        
        for p in data['payments']:
            html_content += f"""
                <tr>
                    <td>{p['date'].strftime('%d/%m/%Y')}</td>
                    <td>{p['concept']}</td>
                    <td>{p['payment_type']}</td>
                    <td style="text-align: right;">{p['amount']:.2f} €</td>
                </tr>
            """
        
        html_content += f"""
                <tr class="total-row">
                    <td colspan="3">Subtotal {student_name}</td>
                    <td style="text-align: right;">{data['total']:.2f} €</td>
                </tr>
            </table>
        </div>
        """
    
    html_content += f"""
        <div class="grand-total">
            TOTAL PAGADO EN {year}: {total_year:.2f} €
        </div>
        
        <div class="legal">
            <p>Este documento tiene validez a efectos de la declaración del Impuesto sobre la Renta 
            de las Personas Físicas (IRPF) según la normativa vigente.</p>
            <p>Los importes indicados corresponden a gastos de enseñanza de idiomas que pueden 
            ser deducibles según la legislación aplicable en cada Comunidad Autónoma.</p>
        </div>
        
        <div class="footer">
            <p>Documento generado automáticamente el {__import__('datetime').date.today().strftime('%d/%m/%Y')}</p>
            <p>Five a Day English Academy - www.fiveadayenglish.com</p>
        </div>
    </body>
    </html>
    """
    
    # Convertir HTML a PDF
    # Usamos weasyprint si está disponible, sino devolvemos el HTML como fallback
    try:
        from weasyprint import HTML
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        # Fallback: devolver HTML como texto si weasyprint no está instalado
        logger.warning("weasyprint no instalado, generando certificado en HTML")
        return html_content.encode('utf-8')


def send_tax_certificate_email(
    parent,
    year: int
) -> bool:
    """
    Genera y envía certificado fiscal para la declaración de la renta.
    El PDF se genera automáticamente con todos los pagos del año.
    
    Args:
        parent: Instancia del modelo Parent (o parent_id como int)
        year: Año fiscal del certificado
    
    Returns:
        True si se envió correctamente
    """
    from core.models import Parent, Payment
    
    # Si se pasa un ID, obtener el objeto Parent
    if isinstance(parent, int):
        try:
            parent = Parent.objects.get(id=parent)
        except Parent.DoesNotExist:
            logger.error(f"Parent con ID {parent} no encontrado")
            return False
    
    # Verificar que el padre tiene pagos en ese año
    payments_count = Payment.objects.filter(
        parent=parent,
        payment_status='completed',
        payment_date__year=year
    ).count()
    
    if payments_count == 0:
        logger.info(f"No hay pagos para {parent.full_name} en {year}, no se envía certificado")
        return False
    
    # Generar el PDF del certificado
    try:
        pdf_content = generate_tax_certificate_pdf(parent, year)
        
        # Determinar si es PDF o HTML (fallback)
        if pdf_content.startswith(b'<!DOCTYPE') or pdf_content.startswith(b'<html'):
            mimetype = 'text/html'
            extension = 'html'
        else:
            mimetype = 'application/pdf'
            extension = 'pdf'
        
        certificate_attachment = (
            f'certificado_fiscal_{year}_{parent.dni}.{extension}',
            pdf_content,
            mimetype
        )
        
    except Exception as e:
        logger.error(f"Error generando PDF para {parent.full_name}: {e}")
        return False
    
    return email_service.send_email(
        template_name='certificado_renta',
        recipients=parent.email,
        subject=f'📄 Certificado Fiscal {year} - Five a Day',
        context={
            'year': year,
            'parent_name': parent.full_name,
        },
        attachments=[certificate_attachment],
        fail_silently=True
    )


def send_all_tax_certificates(year: int) -> Dict[str, int]:
    """
    Envía certificados fiscales a TODOS los padres que tengan pagos en el año.
    
    Args:
        year: Año fiscal
    
    Returns:
        Dict con {sent: N, skipped: N, failed: N}
    """
    from core.models import Parent, Payment
    
    # Obtener todos los padres con pagos completados en ese año
    parents_with_payments = Parent.objects.filter(
        payments__payment_status='completed',
        payments__payment_date__year=year
    ).distinct()
    
    results = {'sent': 0, 'skipped': 0, 'failed': 0}
    
    for parent in parents_with_payments:
        if not parent.email:
            logger.warning(f"⚠️ {parent.full_name}: sin email")
            results['skipped'] += 1
            continue
        
        success = send_tax_certificate_email(parent, year)
        
        if success:
            results['sent'] += 1
            logger.info(f"✅ Certificado enviado a {parent.full_name}")
        else:
            results['failed'] += 1
            logger.error(f"❌ Error enviando a {parent.full_name}")
    
    logger.info(f"📊 Certificados fiscales {year}: {results['sent']} enviados, "
                f"{results['skipped']} omitidos, {results['failed']} fallidos")
    
    return results
