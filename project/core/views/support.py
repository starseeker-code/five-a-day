from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.conf import settings
import json
from datetime import datetime


@require_http_methods(["POST"])
def submit_support_ticket(request):
    """
    Endpoint API para recibir tickets de soporte.
    Envía un email al SUPPORT_EMAIL con los detalles del ticket.
    """
    from django.core.mail import send_mail

    try:
        data = json.loads(request.body)

        category = data.get("category", "exception")
        category_display = data.get("category_display", "otro")
        message = data.get("message", "").strip()
        current_url = data.get("current_url", "/")

        if not message or len(message) < 10:
            return JsonResponse(
                {
                    "success": False,
                    "message": "El mensaje debe tener al menos 10 caracteres",
                },
                status=400,
            )

        username = request.session.get("username", "Anónimo")
        version = settings.APP_VERSION
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        support_email = getattr(settings, "SUPPORT_EMAIL", None)

        if not support_email:
            return JsonResponse(
                {"success": False, "message": "Email de soporte no configurado"},
                status=500,
            )

        subject = f"[{category.upper()}] Ticket de Soporte - Five a Day"

        email_body = f"""
═══════════════════════════════════════════════════════════
                    TICKET DE SOPORTE
═══════════════════════════════════════════════════════════

📋 INFORMACIÓN DEL TICKET
───────────────────────────────────────────────────────────
Tipo:           {category} ({category_display})
Versión:        {version}
Fecha/Hora:     {now}
Usuario:        {username}
Vista actual:   {current_url}

💬 MENSAJE
───────────────────────────────────────────────────────────
{message}

═══════════════════════════════════════════════════════════
                    Five a Day - eVolution
═══════════════════════════════════════════════════════════
"""

        send_mail(
            subject=subject,
            message=email_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[support_email],
            fail_silently=False,
        )

        return JsonResponse(
            {"success": True, "message": "Ticket enviado correctamente"}
        )

    except json.JSONDecodeError:
        return JsonResponse(
            {"success": False, "message": "Datos inválidos"}, status=400
        )
    except Exception as e:
        return JsonResponse(
            {"success": False, "message": f"Error al enviar ticket: {str(e)}"},
            status=500,
        )
