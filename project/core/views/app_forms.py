"""
Email app form views — each view handles GET (show form with email preview)
and POST (send emails to parents).
"""
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
import os
from datetime import date, timedelta

from students.models import Parent, Student, Group
from core.models import HistoryLog
from comms.services.email_service import email_service
from comms.services.email_functions import (
    send_fun_friday_email, send_payment_reminder_email,
    send_vacation_closure_email, send_all_tax_certificates,
    send_quarterly_receipt_email, send_monthly_report, send_welcome_email,
)
from core.constants import DIAS_ES, MESES_ES


def apps_view(request):
    """Vista para la página de aplicaciones/herramientas"""
    return render(request, "apps.html")


# ============================================================================
# FUN FRIDAY - Formulario de envío masivo
# ============================================================================


def fun_friday_form(request):
    """
    Vista para el formulario de Fun Friday.
    GET: Muestra el formulario con valores por defecto
    POST: Valida HTML y envía emails a todos los padres con estudiantes activos
    """
    import html.parser

    today = date.today()
    days_until_friday = (4 - today.weekday()) % 7
    if days_until_friday == 0:
        days_until_friday = 7
    next_friday = today + timedelta(days=days_until_friday)

    parent_count = Parent.objects.filter(children__active=True, children__is_adult=False).distinct().count()

    default_html = """<strong>🎉 ¡SESIÓN DE MANUALIDADES!</strong>
<br><br>
Esta semana haremos manualidades creativas con materiales reciclados.
<br><br>
<em>Los niños deben traer:</em>
<ul>
    <li>Una camiseta vieja</li>
    <li>Tijeras de punta redonda</li>
</ul>
<br>
¡Os esperamos! 🎨"""

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _event_date_str = request.POST.get('event_date', next_friday.isoformat())
            _start_time = request.POST.get('start_time', '17:00')
            _end_time = request.POST.get('end_time', '18:30')
            _meeting_point = request.POST.get('meeting_point', '')
            _activity = request.POST.get('activity_description', default_html)
            try:
                _ed = date.fromisoformat(_event_date_str)
            except (ValueError, TypeError):
                _ed = next_friday
            try:
                _min_age = int(request.POST.get('min_age', 5))
                _max_age = int(request.POST.get('max_age', 12))
            except (ValueError, TypeError):
                _min_age, _max_age = 5, 12
            _ctx = {
                'day_name': DIAS_ES[_ed.weekday()],
                'day_number': _ed.day,
                'month': MESES_ES[_ed.month - 1],
                'start_time': _start_time,
                'end_time': _end_time,
                'activity_description': _activity,
                'meeting_point': _meeting_point,
                'minimum_age': _min_age,
                'maximum_age': _max_age,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/fun_friday.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='fun_friday',
                recipients=_recipients,
                subject=f'[TEST] 🎉 Fun Friday - {_ctx["day_name"].capitalize()} {_ctx["day_number"]} de {_ctx["month"]}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        # Obtener datos del formulario
        event_date_str = request.POST.get("event_date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        meeting_point = request.POST.get("meeting_point", "")
        min_age = request.POST.get("min_age")
        max_age = request.POST.get("max_age")
        activity_description = request.POST.get("activity_description", "")

        if not all(
            [event_date_str, start_time, end_time, min_age, max_age, activity_description]
        ):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description or default_html,
                },
            )

        try:
            parser = html.parser.HTMLParser()
            parser.feed(activity_description)
        except Exception as e:
            messages.error(request, f"❌ HTML inválido: {str(e)}")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        try:
            event_date = date.fromisoformat(event_date_str)
        except ValueError:
            messages.error(request, "❌ Fecha inválida")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        try:
            min_age_int = int(min_age)
            max_age_int = int(max_age)
            if min_age_int > max_age_int:
                raise ValueError("Edad mínima mayor que máxima")
        except ValueError as e:
            messages.error(request, f"❌ Error en rango de edades: {str(e)}")
            return render(
                request,
                "apps/fun_friday_form.html",
                {
                    "next_friday": next_friday.isoformat(),
                    "parent_count": parent_count,
                    "default_html": activity_description,
                },
            )

        day_name = DIAS_ES[event_date.weekday()]
        month_name = MESES_ES[event_date.month - 1]

        parents = Parent.objects.filter(children__active=True).distinct()
        parent_emails = [p.email for p in parents if p.email]

        if not parent_emails:
            messages.warning(request, "⚠️ No hay padres con email para enviar")
            return redirect("home")

        success_count = 0
        error_count = 0

        for email in parent_emails:
            try:
                result = send_fun_friday_email(
                    recipients=email,
                    day_name=day_name,
                    day_number=event_date.day,
                    month=month_name,
                    start_time=start_time,
                    end_time=end_time,
                    activity_description=activity_description,
                    minimum_age=min_age_int,
                    maximum_age=max_age_int,
                    meeting_point=meeting_point if meeting_point else None,
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            HistoryLog.log('email_sent', f'Fun Friday: {success_count} email(s) enviados', icon='mail')
            messages.success(
                request, f"✅ Fun Friday enviado a {success_count} padre(s)"
            )
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")

        return redirect("home")

    # GET - Mostrar formulario con email preview
    email_html = render_to_string('emails/fun_friday.html', {
        'day_name': DIAS_ES[next_friday.weekday()],
        'day_number': next_friday.day,
        'month': MESES_ES[next_friday.month - 1],
        'start_time': '17:00',
        'end_time': '18:30',
        'activity_description': default_html,
        'meeting_point': 'En la puerta principal del centro',
        'minimum_age': 5,
        'maximum_age': 12,
    })
    return render(
        request,
        "apps/fun_friday_form.html",
        {
            "next_friday": next_friday.isoformat(),
            "parent_count": parent_count,
            "default_html": default_html,
            "email_html": email_html,
        },
    )


# ============================================================================
# RECORDATORIO DE PAGO - Formulario de envío
# ============================================================================


def payment_reminder_form(request):
    """
    Vista para enviar recordatorios de pago mensual/trimestral.
    GET: Muestra formulario con valores por defecto
    POST: Envía recordatorio a todos los padres con estudiantes activos
    """
    today = date.today()
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    default_start = today.replace(day=1)
    try:
        default_end = today.replace(day=5)
    except ValueError:
        default_end = today.replace(day=28)

    current_month = MESES_ES[today.month - 1]

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _start_str = request.POST.get('payment_start_date', default_start.isoformat())
            _end_str = request.POST.get('payment_end_date', default_end.isoformat())
            _month = request.POST.get('month', current_month)
            _iban = request.POST.get('iban_number', 'ES00 0000 0000 0000 0000 0000')
            _bizum = request.POST.get('telephone_number_bizum', '600 000 000')
            _cheque = request.POST.get('reduced_price_cheque_idioma', '34€')
            try:
                _sd = date.fromisoformat(_start_str)
                _ed = date.fromisoformat(_end_str)
            except (ValueError, TypeError):
                _sd, _ed = default_start, default_end
            _ctx = {
                'payment_start_day_name': DIAS_ES[_sd.weekday()],
                'payment_start_day_number': _sd.day,
                'payment_end_day_name': DIAS_ES[_ed.weekday()],
                'payment_end_day_number': _ed.day,
                'month': _month,
                'iban_number': _iban,
                'reduced_price_cheque_idioma': _cheque,
                'telephone_number_bizum': _bizum,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/payment_reminder.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='payment_reminder',
                recipients=_recipients,
                subject=f'[TEST] 💰 Recordatorio de Pago - {_month.title()}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        payment_start_date_str = request.POST.get("payment_start_date")
        payment_end_date_str = request.POST.get("payment_end_date")
        month = request.POST.get("month", current_month)
        iban_number = request.POST.get("iban_number", "")
        telephone_number_bizum = request.POST.get("telephone_number_bizum", "")
        reduced_price_cheque_idioma = request.POST.get("reduced_price_cheque_idioma", "34€")

        if not all([payment_start_date_str, payment_end_date_str, iban_number, telephone_number_bizum]):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
        else:
            try:
                start_date = date.fromisoformat(payment_start_date_str)
                end_date = date.fromisoformat(payment_end_date_str)
            except ValueError:
                messages.error(request, "❌ Fecha inválida")
                return redirect("payment_reminder_form")

            parents = Parent.objects.filter(children__active=True).distinct()
            parent_emails = [p.email for p in parents if p.email]

            if not parent_emails:
                messages.warning(request, "⚠️ No hay padres con email para enviar")
                return redirect("apps")

            success_count = 0
            error_count = 0
            for email_addr in parent_emails:
                try:
                    result = send_payment_reminder_email(
                        recipients=email_addr,
                        payment_start_day_name=DIAS_ES[start_date.weekday()],
                        payment_start_day_number=start_date.day,
                        payment_end_day_name=DIAS_ES[end_date.weekday()],
                        payment_end_day_number=end_date.day,
                        month=month,
                        iban_number=iban_number,
                        reduced_price_cheque_idioma=reduced_price_cheque_idioma,
                        telephone_number_bizum=telephone_number_bizum,
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

            if success_count > 0:
                HistoryLog.log('email_sent', f'Recordatorio de pago: {success_count} email(s) enviados', icon='mail')
                messages.success(request, f"✅ Recordatorio enviado a {success_count} padre(s)")
            if error_count > 0:
                messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
            return redirect("apps")

    email_html = render_to_string('emails/payment_reminder.html', {
        'payment_start_day_name': DIAS_ES[default_start.weekday()],
        'payment_start_day_number': default_start.day,
        'payment_end_day_name': DIAS_ES[default_end.weekday()],
        'payment_end_day_number': default_end.day,
        'month': current_month,
        'iban_number': 'ES00 0000 0000 0000 0000 0000',
        'reduced_price_cheque_idioma': '34€',
        'telephone_number_bizum': '600 000 000',
    })
    return render(request, "apps/payment_reminder_form.html", {
        "parent_count": parent_count,
        "default_start_date": default_start.isoformat(),
        "default_end_date": default_end.isoformat(),
        "months": MESES_ES,
        "current_month": current_month,
        "default_iban": "",
        "default_bizum": "",
        "default_cheque_price": "34€",
        "email_html": email_html,
    })


# ============================================================================
# CIERRE POR VACACIONES - Formulario de envío
# ============================================================================


def vacation_closure_form(request):
    """
    Vista para enviar avisos de cierre por vacaciones.
    GET: Muestra formulario
    POST: Envía aviso a todos los padres con estudiantes activos
    """
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _cs_str = request.POST.get('closure_start_date', '')
            _ce_str = request.POST.get('closure_end_date', '')
            _r_str = request.POST.get('reopening_date', '')
            _reason = request.POST.get('closure_reason', 'Vacaciones')
            try:
                _cs = date.fromisoformat(_cs_str)
                _ce = date.fromisoformat(_ce_str)
                _ro = date.fromisoformat(_r_str)
            except (ValueError, TypeError):
                _cs = date.today()
                _ce = _cs + timedelta(days=7)
                _ro = _ce + timedelta(days=3)
            _ctx = {
                'start_closure_day_name': DIAS_ES[_cs.weekday()],
                'start_closure_day_number': _cs.day,
                'end_closure_day_name': DIAS_ES[_ce.weekday()],
                'end_closure_day_number': _ce.day,
                'month_closure': MESES_ES[_cs.month - 1],
                'closure_reason': _reason,
                'reopening_day_name': DIAS_ES[_ro.weekday()],
                'reopening_day_number': _ro.day,
                'month_reopening': MESES_ES[_ro.month - 1],
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/vacation_closure.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='vacation_closure',
                recipients=_recipients,
                subject=f'[TEST] 🏖️ Cierre por {_reason} - Five a Day',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        closure_start_str = request.POST.get("closure_start_date")
        closure_end_str = request.POST.get("closure_end_date")
        closure_reason = request.POST.get("closure_reason", "")
        reopening_str = request.POST.get("reopening_date")

        if not all([closure_start_str, closure_end_str, closure_reason, reopening_str]):
            messages.error(request, "❌ Todos los campos obligatorios son requeridos")
        else:
            try:
                closure_start = date.fromisoformat(closure_start_str)
                closure_end = date.fromisoformat(closure_end_str)
                reopening = date.fromisoformat(reopening_str)
            except ValueError:
                messages.error(request, "❌ Fecha inválida")
                return redirect("vacation_closure_form")

            parents = Parent.objects.filter(children__active=True).distinct()
            parent_emails = [p.email for p in parents if p.email]

            if not parent_emails:
                messages.warning(request, "⚠️ No hay padres con email para enviar")
                return redirect("apps")

            success_count = 0
            error_count = 0
            for email_addr in parent_emails:
                try:
                    result = send_vacation_closure_email(
                        recipients=email_addr,
                        start_closure_day_name=DIAS_ES[closure_start.weekday()],
                        start_closure_day_number=closure_start.day,
                        end_closure_day_name=DIAS_ES[closure_end.weekday()],
                        end_closure_day_number=closure_end.day,
                        month_closure=MESES_ES[closure_start.month - 1],
                        closure_reason=closure_reason,
                        reopening_day_name=DIAS_ES[reopening.weekday()],
                        reopening_day_number=reopening.day,
                        month_reopening=MESES_ES[reopening.month - 1],
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

            if success_count > 0:
                HistoryLog.log('email_sent', f'Cierre por vacaciones: {success_count} email(s) enviados', icon='mail')
                messages.success(request, f"✅ Aviso de cierre enviado a {success_count} padre(s)")
            if error_count > 0:
                messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
            return redirect("apps")

    email_html = render_to_string('emails/vacation_closure.html', {
        'start_closure_day_name': 'lunes',
        'start_closure_day_number': 23,
        'end_closure_day_name': 'viernes',
        'end_closure_day_number': 3,
        'month_closure': 'diciembre',
        'closure_reason': 'Navidad',
        'reopening_day_name': 'lunes',
        'reopening_day_number': 8,
        'month_reopening': 'enero',
    })
    return render(request, "apps/vacation_closure_form.html", {
        "parent_count": parent_count,
        "email_html": email_html,
    })


# ============================================================================
# CERTIFICADO RENTA - Generación y envío
# ============================================================================


def tax_certificate_form(request):
    """
    Vista para generar y enviar certificados fiscales.
    GET: Muestra formulario con año por defecto
    POST: Genera y envía certificados a todos los padres con pagos
    """
    from billing.models import Payment

    today = date.today()
    default_year = today.year - 1

    parents_with_payments = Parent.objects.filter(
        payments__payment_status='completed',
        payments__payment_date__year=default_year
    ).distinct().count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _year = int(request.POST.get('year', default_year))
            _ctx = {'year': _year, 'parent_name': 'Nombre del padre'}
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/tax_certificate.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='tax_certificate',
                recipients=_recipients,
                subject=f'[TEST] 📋 Certificado de Renta {_year} - Five a Day',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        year = int(request.POST.get("year", default_year))
        results = send_all_tax_certificates(year)

        if results['sent'] > 0:
            HistoryLog.log('email_sent', f'Certificado de renta: {results["sent"]} email(s) enviados', icon='mail')
            messages.success(request, f"✅ Certificados enviados a {results['sent']} padre(s)")
        if results.get('skipped', 0) > 0:
            messages.info(request, f"ℹ️ {results['skipped']} padre(s) omitidos (sin email)")
        if results.get('failed', 0) > 0:
            messages.warning(request, f"⚠️ {results['failed']} certificado(s) fallaron")
        return redirect("apps")

    email_html = render_to_string('emails/tax_certificate.html', {
        'year': default_year,
        'parent_name': 'Nombre del padre',
    })
    return render(request, "apps/tax_certificate_form.html", {
        "default_year": default_year,
        "parents_with_payments": parents_with_payments,
        "email_html": email_html,
    })


# ============================================================================
# INFORME MENSUAL - Formulario de envío
# ============================================================================


def monthly_report_form(request):
    """
    Vista para enviar informes mensuales a los padres.
    GET: Muestra formulario con mes/año actual
    POST: Envía informes personalizados a cada padre
    """
    today = date.today()
    current_month = MESES_ES[today.month - 1]
    parent_count = Parent.objects.filter(children__active=True).distinct().count()
    total_students = Student.objects.filter(active=True).count()
    total_groups = Group.objects.filter(active=True).count()

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _month = request.POST.get('month', current_month)
            try:
                _year = int(request.POST.get('year', today.year))
            except (ValueError, TypeError):
                _year = today.year
            _ctx = {
                'month': _month,
                'year': _year,
                'parent_name': 'Nombre del padre',
                'students': [{'name': 'Alumno Ejemplo', 'group': 'Grupo A'}],
                'total_students': 1,
            }
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/monthly_report.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='monthly_report',
                recipients=_recipients,
                subject=f'[TEST] 📊 Informe Mensual - {_month.title()} {_year}',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        month = request.POST.get("month", current_month)
        year = int(request.POST.get("year", today.year))

        parents = Parent.objects.filter(
            children__active=True
        ).distinct().prefetch_related('children__group')

        success_count = 0
        error_count = 0
        for parent in parents:
            if not parent.email:
                continue
            students_data = [
                {'name': s.full_name, 'group': s.group.group_name if s.group else 'Sin grupo'}
                for s in parent.children.filter(active=True)
            ]
            try:
                result = send_monthly_report(
                    recipient=parent.email,
                    report_data={
                        'month': month,
                        'year': year,
                        'parent_name': parent.full_name,
                        'students': students_data,
                        'total_students': len(students_data),
                    }
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            HistoryLog.log('email_sent', f'Informe mensual: {success_count} email(s) enviados', icon='mail')
            messages.success(request, f"✅ Informes enviados a {success_count} padre(s)")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} informe(s) no pudieron enviarse")
        return redirect("apps")

    email_html = render_to_string('emails/monthly_report.html', {
        'month': current_month,
        'year': today.year,
        'parent_name': 'Nombre del padre',
        'students': [{'name': 'Alumno Ejemplo', 'group': 'Grupo A'}],
        'total_students': 1,
    })
    return render(request, "apps/monthly_report_form.html", {
        "months": MESES_ES,
        "current_month": current_month,
        "current_year": today.year,
        "parent_count": parent_count,
        "total_students": total_students,
        "total_groups": total_groups,
        "email_html": email_html,
    })


# ============================================================================
# BIENVENIDA - Email de alta de estudiante
# ============================================================================


def welcome_form(request):
    """Merged into enrollment_form — redirect all traffic there."""
    return redirect("enrollment_form")


# ============================================================================
# CUMPLEAÑOS - Gestión de emails de cumpleaños
# ============================================================================


def birthday_form(request):
    """
    Vista para gestionar y enviar manualmente emails de cumpleaños.
    GET: Muestra cumpleaños de hoy y del mes, con preview
    POST: Envía manualmente los emails de cumpleaños de hoy
    """
    today = date.today()
    birthday_students = Student.objects.filter(
        birth_date__month=today.month,
        birth_date__day=today.day,
        active=True
    ).select_related('group')

    month_birthdays = Student.objects.filter(
        birth_date__month=today.month,
        active=True
    ).select_related('group').order_by('birth_date__day')

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _name = birthday_students.first().first_name if birthday_students.exists() else 'Alumno Ejemplo'
            _ctx = {'name': _name}
            if action == 'preview':
                return JsonResponse({'html': render_to_string('emails/happy_birthday.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name='happy_birthday',
                recipients=_recipients,
                subject=f'[TEST] 🎉 ¡Feliz Cumpleaños {_name}!',
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        if not birthday_students.exists():
            messages.info(request, "ℹ️ No hay cumpleaños hoy")
            return redirect("birthday_form")

        success_count = 0
        error_count = 0
        for student in birthday_students:
            parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
            if not parent:
                continue
            try:
                result = email_service.send_email(
                    template_name='happy_birthday',
                    recipients=parent.email,
                    subject=f'🎉 ¡Feliz Cumpleaños {student.first_name}!',
                    context={'name': student.first_name}
                )
                if result:
                    success_count += 1
                else:
                    error_count += 1
            except Exception:
                error_count += 1

        if success_count > 0:
            HistoryLog.log('email_sent', f'Cumpleaños: {success_count} email(s) enviados', icon='mail')
            messages.success(request, f"✅ Email de cumpleaños enviado a {success_count} estudiante(s)")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} email(s) no pudieron enviarse")
        return redirect("birthday_form")

    email_html = render_to_string('emails/happy_birthday.html', {
        'name': 'Alumno',
    })
    return render(request, "apps/birthday_form.html", {
        "today": today.strftime('%d/%m/%Y'),
        "birthday_students": birthday_students,
        "month_birthdays": month_birthdays,
        "email_html": email_html,
    })


# ============================================================================
# RECIBOS - Generación y envío trimestral/mensual
# ============================================================================


def receipts_form(request):
    """
    Vista para enviar recibos trimestrales (niños) o mensuales (adultos).
    GET: Muestra formulario con opciones de trimestre/mes
    POST: Envía recibos a los padres correspondientes
    """
    today = date.today()
    current_month = MESES_ES[today.month - 1]
    parent_count = Parent.objects.filter(children__active=True).distinct().count()

    quarter_idx = (today.month - 1) // 3
    quarter_start = quarter_idx * 3
    quarter_months = [MESES_ES[quarter_start], MESES_ES[quarter_start + 1], MESES_ES[quarter_start + 2]]

    if request.method == "POST":
        action = request.POST.get('action', '')
        if action in ('preview', 'test_send'):
            _rtype = request.POST.get('receipt_type', 'quarterly_child')
            if _rtype == 'quarterly_child':
                _m1 = request.POST.get('month_1', quarter_months[0])
                _m2 = request.POST.get('month_2', quarter_months[1])
                _m3 = request.POST.get('month_3', quarter_months[2])
                _template = 'receipt_quarterly_child'
                _ctx = {'student_name': 'Alumno Ejemplo', 'month_1': _m1, 'month_2': _m2, 'month_3': _m3}
                _subject = f'[TEST] 🧾 Recibo Trimestral - {_m1.title()}/{_m2.title()}/{_m3.title()}'
            else:
                _adm = request.POST.get('adult_month', current_month)
                _template = 'receipt_adult'
                _ctx = {'month': _adm}
                _subject = f'[TEST] 🧾 Recibo Mensual - {_adm.title()}'
            if action == 'preview':
                return JsonResponse({'html': render_to_string(f'emails/{_template}.html', _ctx)})
            _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
            _recipients = [r for r in [_t1, _t2] if r]
            if not _recipients:
                return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
            _ok = email_service.send_email(
                template_name=_template,
                recipients=_recipients,
                subject=_subject,
                context=_ctx,
            )
            if _ok:
                return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
            return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        receipt_type = request.POST.get("receipt_type", "quarterly_child")

        if receipt_type == "quarterly_child":
            month_1 = request.POST.get("month_1", quarter_months[0])
            month_2 = request.POST.get("month_2", quarter_months[1])
            month_3 = request.POST.get("month_3", quarter_months[2])

            parents = Parent.objects.filter(
                children__active=True
            ).distinct().prefetch_related('children')

            success_count = 0
            error_count = 0
            for parent in parents:
                if not parent.email:
                    continue
                for student in parent.children.filter(active=True):
                    try:
                        result = send_quarterly_receipt_email(
                            parent_email=parent.email,
                            student_name=student.full_name,
                            month_1=month_1,
                            month_2=month_2,
                            month_3=month_3,
                        )
                        if result:
                            success_count += 1
                        else:
                            error_count += 1
                    except Exception:
                        error_count += 1
        else:
            adult_month = request.POST.get("adult_month", current_month)
            parents = Parent.objects.filter(
                children__active=True
            ).distinct()

            success_count = 0
            error_count = 0
            for parent in parents:
                if not parent.email:
                    continue
                try:
                    result = email_service.send_email(
                        template_name='receipt_adult',
                        recipients=parent.email,
                        subject=f'🧾 Recibo Mensual - {adult_month.title()}',
                        context={'month': adult_month},
                    )
                    if result:
                        success_count += 1
                    else:
                        error_count += 1
                except Exception:
                    error_count += 1

        if success_count > 0:
            HistoryLog.log('email_sent', f'Recibos: {success_count} email(s) enviados', icon='mail')
            messages.success(request, f"✅ Recibos enviados: {success_count}")
        if error_count > 0:
            messages.warning(request, f"⚠️ {error_count} recibo(s) no pudieron enviarse")
        return redirect("apps")

    email_html = render_to_string('emails/receipt_quarterly_child.html', {
        'student_name': 'Alumno Ejemplo',
        'month_1': quarter_months[0],
        'month_2': quarter_months[1],
        'month_3': quarter_months[2],
    })
    return render(request, "apps/receipts_form.html", {
        "months": MESES_ES,
        "current_month": current_month,
        "quarter_months": quarter_months,
        "parent_count": parent_count,
        "email_html": email_html,
    })


# ============================================================================
# MATRÍCULAS - Confirmación de matrícula
# ============================================================================


def enrollment_form(request):
    """
    Vista para enviar confirmación de matrícula manualmente.
    GET: Muestra formulario con selector de estudiante
    POST: Envía confirmación al padre del estudiante seleccionado
    """
    today = date.today()
    current_month = MESES_ES[today.month - 1]
    students = Student.objects.filter(active=True).select_related('group').order_by('last_name', 'first_name')

    if today.month >= 9:
        default_academic_year = f"{today.year}-{today.year + 1}"
    else:
        default_academic_year = f"{today.year - 1}-{today.year}"

    if request.method == "POST":
        action = request.POST.get('action', '')
        email_type = request.POST.get('email_type', 'enrollment')

        if action in ('preview', 'test_send'):
            _student_id = request.POST.get('student_id')
            if email_type == 'welcome':
                _ctx = {
                    'parent_name': 'Nombre del padre',
                    'student_name': 'Nombre del alumno',
                    'group_name': 'Grupo A',
                    'enrollment_type': 'Mensual',
                    'schedule_type': 'Jornada completa',
                    'start_date': '01/09/2025',
                }
                if _student_id:
                    try:
                        _s = Student.objects.select_related('group').get(id=_student_id)
                        _p = _s.parents.exclude(email='').exclude(email__isnull=True).first()
                        _ctx['student_name'] = _s.full_name
                        if _p:
                            _ctx['parent_name'] = _p.full_name
                        if _s.group:
                            _ctx['group_name'] = _s.group.group_name
                    except Exception:
                        pass
                if action == 'preview':
                    return JsonResponse({'html': render_to_string('emails/welcome_student.html', _ctx)})
                _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
                _recipients = [r for r in [_t1, _t2] if r]
                if not _recipients:
                    return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
                _ok = email_service.send_email(
                    template_name='welcome_student',
                    recipients=_recipients,
                    subject=f'[TEST] 🎉 Bienvenida a Five a Day - {_ctx["student_name"]}',
                    context=_ctx,
                )
                if _ok:
                    return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
                return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})
            else:
                _etype = request.POST.get('enrollment_type', 'child')
                _gender = request.POST.get('gender', 'm')
                _ay = request.POST.get('academic_year', default_academic_year)
                _month = request.POST.get('month', current_month)
                _student_name = 'Alumno Ejemplo'
                if _student_id:
                    try:
                        _s = Student.objects.get(id=_student_id)
                        _student_name = _s.full_name
                    except Exception:
                        pass
                _template = 'enrollment_child' if _etype == 'child' else 'enrollment_adult'
                _ctx = {'student': _student_name, 'genero': _gender, 'academic_year': _ay, 'month': _month}
                if action == 'preview':
                    return JsonResponse({'html': render_to_string(f'emails/{_template}.html', _ctx)})
                _t1, _t2 = os.getenv('EMAIL_TEST_1', ''), os.getenv('EMAIL_TEST_2', '')
                _recipients = [r for r in [_t1, _t2] if r]
                if not _recipients:
                    return JsonResponse({'success': False, 'message': '❌ EMAIL_TEST_1/EMAIL_TEST_2 no configurados'})
                _ok = email_service.send_email(
                    template_name=_template,
                    recipients=_recipients,
                    subject=f'[TEST] 🎉 Confirmación de Matrícula - {_student_name}',
                    context=_ctx,
                )
                if _ok:
                    return JsonResponse({'success': True, 'message': f'✅ Email de prueba enviado a {", ".join(_recipients)}'})
                return JsonResponse({'success': False, 'message': '❌ Error al enviar el email de prueba'})

        student_id = request.POST.get("student_id")
        if not student_id:
            messages.error(request, "❌ Selecciona un estudiante")
        elif email_type == 'welcome':
            try:
                student = Student.objects.select_related('group').prefetch_related('parents').get(id=student_id)
                parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
                if not parent:
                    messages.error(request, f"❌ {student.full_name} no tiene padre con email registrado")
                else:
                    result = send_welcome_email(
                        parent_email=parent.email,
                        parent_name=parent.full_name,
                        student_name=student.full_name,
                        group_name=student.group.group_name if student.group else None,
                    )
                    if result:
                        HistoryLog.log('email_sent', f'Bienvenida: 1 email enviado ({student.full_name})', icon='mail')
                        messages.success(request, f"✅ Email de bienvenida enviado a {parent.email}")
                    else:
                        messages.error(request, "❌ Error al enviar el email")
            except Student.DoesNotExist:
                messages.error(request, "❌ Estudiante no encontrado")
        else:
            enrollment_type = request.POST.get("enrollment_type", "child")
            gender = request.POST.get("gender", "m")
            academic_year = request.POST.get("academic_year", default_academic_year)
            month = request.POST.get("month", current_month)
            try:
                student = Student.objects.prefetch_related('parents').get(id=student_id)
                parent = student.parents.exclude(email='').exclude(email__isnull=True).first()
                if not parent:
                    messages.error(request, f"❌ {student.full_name} no tiene padre con email registrado")
                else:
                    template = 'enrollment_child' if enrollment_type == 'child' else 'enrollment_adult'
                    result = email_service.send_email(
                        template_name=template,
                        recipients=parent.email,
                        subject=f'🎉 Confirmación de Matrícula - {student.full_name}',
                        context={
                            'student': student.full_name,
                            'genero': gender,
                            'academic_year': academic_year,
                            'month': month,
                        },
                    )
                    if result:
                        HistoryLog.log('email_sent', f'Confirmación matrícula: 1 email enviado ({student.full_name})', icon='mail')
                        messages.success(request, f"✅ Confirmación de matrícula enviada a {parent.email}")
                    else:
                        messages.error(request, "❌ Error al enviar el email")
            except Student.DoesNotExist:
                messages.error(request, "❌ Estudiante no encontrado")
        return redirect("enrollment_form")

    email_html = render_to_string('emails/welcome_student.html', {
        'parent_name': 'Nombre del padre',
        'student_name': 'Nombre del alumno',
        'group_name': 'Grupo A',
        'enrollment_type': 'Mensual',
        'schedule_type': 'Jornada completa',
        'start_date': '01/09/2025',
    })
    return render(request, "apps/enrollment_form.html", {
        "students": students,
        "months": MESES_ES,
        "current_month": current_month,
        "default_academic_year": default_academic_year,
        "email_html": email_html,
    })
