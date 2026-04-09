"""
Convenience email functions for Five a Day.
Each function sends a specific type of email using the shared EmailService.

Moved from core/email.py as part of the comms app split.

NOTE: Templates (emails/*.html) still live in the core templates directory for now.
They should be moved to comms/templates/ in a future step.
"""
from typing import List, Dict, Optional, Union
import logging
import os

from comms.services.email_service import email_service

logger = logging.getLogger(__name__)


# ============================================================================
# 1. BIRTHDAY - Felicitacion de cumpleanos
# ============================================================================

def send_birthday_email(recipient: str, name: str) -> bool:
    """Envia email de cumpleanos"""
    return email_service.send_email(
        template_name='happy_birthday',
        recipients=recipient,
        subject=f'🎉 ¡Feliz Cumpleaños {name}!',
        context={'name': name}
    )


# ============================================================================
# 2. PAYMENT REMINDER (simple) - Recordatorio de pago pendiente
# ============================================================================

def send_payment_reminder(recipient: str, student_name: str, amount: float, due_date: str) -> bool:
    """Envia recordatorio de pago pendiente"""
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


# ============================================================================
# 3. MONTHLY REPORT - Reporte mensual
# ============================================================================

def send_monthly_report(recipient: str, report_data: Dict) -> bool:
    """Envia reporte mensual"""
    return email_service.send_email(
        template_name='monthly_report',
        recipients=recipient,
        subject='📊 Reporte Mensual - Five a Day',
        context=report_data
    )


# ============================================================================
# 4. WELCOME - Bienvenida a nuevo estudiante
# ============================================================================

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
    Envia email de bienvenida cuando se matricula un nuevo estudiante.

    Args:
        parent_email: Email del padre/tutor
        parent_name: Nombre del padre/tutor
        student_name: Nombre del estudiante
        group_name: Nombre del grupo asignado
        enrollment_type: Tipo de matricula
        schedule_type: Tipo de horario
        start_date: Fecha de inicio del periodo

    Returns:
        True si se envio correctamente
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
        fail_silently=True
    )


# ============================================================================
# 5. ENROLLMENT CONFIRMATION - Confirmacion de matricula nino
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
    Envia email de confirmacion de matricula para ninos.

    Args:
        parent_email: Email del padre/tutor
        student_name: Nombre del estudiante
        gender: Genero del estudiante ("m" o "f")
        academic_year: Ano academico (ej: "2024-2025")
        month: Mes de inicio
        attachments: Lista de tuplas (filename, content, mimetype) con PDFs adjuntos

    Returns:
        True si se envio correctamente
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
# 6. FUN FRIDAY - Invitacion a eventos
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
    Envia invitacion a evento Fun Friday.

    Args:
        recipients: Email(s) de los padres
        day_name: Nombre del dia (ej: "viernes")
        day_number: Numero del dia
        month: Nombre del mes
        start_time: Hora de inicio (ej: "17:00")
        end_time: Hora de fin (ej: "18:30")
        activity_description: Descripcion de la actividad
        minimum_age: Edad minima
        maximum_age: Edad maxima
        meeting_point: Punto de encuentro (opcional)
        event_image_path: Ruta a imagen del evento (opcional)

    Returns:
        True si se envio correctamente
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
# 7. PAYMENT REMINDER (full) - Recordatorio de pago mensual/trimestral
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
    Envia recordatorio de pago mensual/trimestral.

    Args:
        recipients: Email(s) de los padres
        payment_start_day_name: Nombre del dia inicio de pago
        payment_start_day_number: Numero del dia inicio
        payment_end_day_name: Nombre del dia fin de pago
        payment_end_day_number: Numero del dia fin
        month: Mes del pago
        iban_number: Numero IBAN para transferencias
        reduced_price_cheque_idioma: Precio reducido con cheque idioma
        telephone_number_bizum: Telefono para Bizum
        attachments: Lista de PDFs (tarifas, instrucciones)

    Returns:
        True si se envio correctamente
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
# 8. QUARTERLY RECEIPT - Recibo trimestral nino
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
    Envia recibo trimestral para ninos.

    Args:
        parent_email: Email del padre/tutor
        student_name: Nombre del estudiante
        month_1: Primer mes del trimestre
        month_2: Segundo mes del trimestre
        month_3: Tercer mes del trimestre
        receipt_pdf: Tupla (filename, content, mimetype) con el recibo PDF

    Returns:
        True si se envio correctamente
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
# 9. VACATION CLOSURE - Aviso de cierre por vacaciones
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
    Envia aviso de cierre por vacaciones.

    Args:
        recipients: Email(s) de los padres
        start_closure_day_name: Nombre del dia de inicio de cierre
        start_closure_day_number: Numero del dia de inicio
        end_closure_day_name: Nombre del dia de fin de cierre
        end_closure_day_number: Numero del dia de fin
        month_closure: Mes del cierre
        closure_reason: Motivo del cierre (ej: "Navidad", "Semana Santa")
        reopening_day_name: Nombre del dia de reapertura
        reopening_day_number: Numero del dia de reapertura
        month_reopening: Mes de reapertura

    Returns:
        True si se envio correctamente
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
# 10. TAX CERTIFICATE - Certificado fiscal anual
# ============================================================================

def generate_tax_certificate_pdf(parent, year: int) -> bytes:
    """
    Genera un PDF con el certificado fiscal para la declaracion de la renta.
    Incluye todos los pagos realizados por el padre durante el ano.

    Args:
        parent: Instancia del modelo Parent
        year: Ano fiscal

    Returns:
        Bytes del PDF generado
    """
    from io import BytesIO
    from billing.models import Payment
    from decimal import Decimal

    # Obtener todos los pagos completados del padre en ese ano
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
            <p>C/Hermanos Jimenez 25 - 02004 Albacete</p>
            <p>CIF: XXXXXXXXX | Tel: 967 049 096</p>
        </div>

        <h2 style="text-align: center;">CERTIFICADO FISCAL - AÑO {year}</h2>

        <div class="info-box">
            <p><strong>Titular:</strong> {parent.full_name}</p>
            <p><strong>DNI:</strong> {parent.dni}</p>
            <p><strong>Periodo:</strong> 01/01/{year} - 31/12/{year}</p>
        </div>

        <p>Five a Day English Academy certifica que durante el ano <strong>{year}</strong>
        se han recibido los siguientes pagos en concepto de servicios educativos:</p>
    """

    for student_name, data in students_data.items():
        html_content += f"""
        <div class="student-section">
            <p class="student-name">Estudiante: {student_name}</p>
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
                    <td style="text-align: right;">{p['amount']:.2f} EUR</td>
                </tr>
            """

        html_content += f"""
                <tr class="total-row">
                    <td colspan="3">Subtotal {student_name}</td>
                    <td style="text-align: right;">{data['total']:.2f} EUR</td>
                </tr>
            </table>
        </div>
        """

    html_content += f"""
        <div class="grand-total">
            TOTAL PAGADO EN {year}: {total_year:.2f} EUR
        </div>

        <div class="legal">
            <p>Este documento tiene validez a efectos de la declaracion del Impuesto sobre la Renta
            de las Personas Fisicas (IRPF) segun la normativa vigente.</p>
            <p>Los importes indicados corresponden a gastos de ensenanza de idiomas que pueden
            ser deducibles segun la legislacion aplicable en cada Comunidad Autonoma.</p>
        </div>

        <div class="footer">
            <p>Documento generado automaticamente el {__import__('datetime').date.today().strftime('%d/%m/%Y')}</p>
            <p>Five a Day English Academy - www.fiveadayenglish.com</p>
        </div>
    </body>
    </html>
    """

    # Convertir HTML a PDF
    # Usamos weasyprint si esta disponible, sino devolvemos el HTML como fallback
    try:
        from weasyprint import HTML
        pdf_buffer = BytesIO()
        HTML(string=html_content).write_pdf(pdf_buffer)
        return pdf_buffer.getvalue()
    except ImportError:
        # Fallback: devolver HTML como texto si weasyprint no esta instalado
        logger.warning("weasyprint no instalado, generando certificado en HTML")
        return html_content.encode('utf-8')


def send_tax_certificate_email(
    parent,
    year: int
) -> bool:
    """
    Genera y envia certificado fiscal para la declaracion de la renta.
    El PDF se genera automaticamente con todos los pagos del ano.

    Args:
        parent: Instancia del modelo Parent (o parent_id como int)
        year: Ano fiscal del certificado

    Returns:
        True si se envio correctamente
    """
    from students.models import Parent
    from billing.models import Payment

    # Si se pasa un ID, obtener el objeto Parent
    if isinstance(parent, int):
        try:
            parent = Parent.objects.get(id=parent)
        except Parent.DoesNotExist:
            logger.error(f"Parent con ID {parent} no encontrado")
            return False

    # Verificar que el padre tiene pagos en ese ano
    payments_count = Payment.objects.filter(
        parent=parent,
        payment_status='completed',
        payment_date__year=year
    ).count()

    if payments_count == 0:
        logger.info(f"No hay pagos para {parent.full_name} en {year}, no se envia certificado")
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
        subject=f'Certificado Fiscal {year} - Five a Day',
        context={
            'year': year,
            'parent_name': parent.full_name,
        },
        attachments=[certificate_attachment],
        fail_silently=True
    )


def send_all_tax_certificates(year: int) -> Dict[str, int]:
    """
    Envia certificados fiscales a TODOS los padres que tengan pagos en el ano.

    Args:
        year: Ano fiscal

    Returns:
        Dict con {sent: N, skipped: N, failed: N}
    """
    from students.models import Parent
    from billing.models import Payment

    # Obtener todos los padres con pagos completados en ese ano
    parents_with_payments = Parent.objects.filter(
        payments__payment_status='completed',
        payments__payment_date__year=year
    ).distinct()

    results = {'sent': 0, 'skipped': 0, 'failed': 0}

    for parent in parents_with_payments:
        if not parent.email:
            logger.warning(f"{parent.full_name}: sin email")
            results['skipped'] += 1
            continue

        success = send_tax_certificate_email(parent, year)

        if success:
            results['sent'] += 1
            logger.info(f"Certificado enviado a {parent.full_name}")
        else:
            results['failed'] += 1
            logger.error(f"Error enviando a {parent.full_name}")

    logger.info(f"Certificados fiscales {year}: {results['sent']} enviados, "
                f"{results['skipped']} omitidos, {results['failed']} fallidos")

    return results
