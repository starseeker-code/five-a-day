"""
Middleware — authentication and QA error reporting.
"""
import logging
import traceback

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.urls import reverse

logger = logging.getLogger(__name__)


class QAErrorEmailMiddleware:
    """
    When QAConfiguration.error_email_enabled is True, catches unhandled
    exceptions and sends a detailed report to SUPPORT_EMAIL.
    Must be placed AFTER SecurityMiddleware and BEFORE other app middleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        try:
            from core.models import QAConfiguration
            config = QAConfiguration.get_config()
            if not config.error_email_enabled:
                return None

            support_email = getattr(settings, "SUPPORT_EMAIL", None)
            if not support_email:
                return None

            tb = traceback.format_exception(type(exception), exception, exception.__traceback__)
            tb_str = "".join(tb)

            username = request.session.get("username", "anonymous") if hasattr(request, "session") else "—"
            method = request.method
            path = request.get_full_path()
            body_preview = ""
            try:
                body_preview = request.body[:500].decode("utf-8", errors="replace")
            except Exception:
                pass

            subject = f"[ERROR] {type(exception).__name__} at {path}"
            body = (
                f"AUTOMATED ERROR REPORT — Five a Day QA\n"
                f"{'=' * 60}\n\n"
                f"Exception:   {type(exception).__name__}: {exception}\n"
                f"Path:        {method} {path}\n"
                f"User:        {username}\n"
                f"Version:     {settings.APP_VERSION}\n"
                f"Environment: {settings.ENVIRONMENT}\n"
                f"Debug:       {settings.DEBUG}\n"
                f"Server time: {__import__('datetime').datetime.now():%Y-%m-%d %H:%M:%S}\n\n"
                f"REQUEST BODY (first 500 chars):\n"
                f"{body_preview or '(empty)'}\n\n"
                f"TRACEBACK:\n"
                f"{'-' * 60}\n"
                f"{tb_str}\n"
                f"{'=' * 60}\n"
            )

            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[support_email],
                fail_silently=True,
            )
        except Exception:
            logger.exception("QAErrorEmailMiddleware failed to send error email")

        return None  # Let Django's default error handling continue


class SimpleAuthMiddleware:
    """
    Middleware que requiere autenticación para acceder a cualquier vista
    excepto la página de login y health check
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # URLs públicas que no requieren autenticación
        login_url = reverse('login')
        public_prefixes = [
            '/health/',         # Health check para Render
            '/static/',         # Archivos estáticos
            '/media/',          # Archivos media
            '/auth/google/',    # Google OAuth flow (includes /callback/)
        ]

        # Verificar si la URL actual es pública
        path = request.path
        is_public = path == login_url or any(path.startswith(prefix) for prefix in public_prefixes)
        
        # Si no es pública y no está autenticado, redirigir a login
        if not is_public and not request.session.get('is_authenticated'):
            return redirect('login')
        
        response = self.get_response(request)
        return response
