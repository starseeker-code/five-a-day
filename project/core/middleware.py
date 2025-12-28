"""
Middleware de autenticación simple
Protege todas las rutas excepto /login/ y /health/
"""
from django.shortcuts import redirect
from django.urls import reverse


class SimpleAuthMiddleware:
    """
    Middleware que requiere autenticación para acceder a cualquier vista
    excepto la página de login y health check
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # URLs públicas que no requieren autenticación
        public_urls = [
            reverse('login'),
            '/health/',  # Health check para Render
            '/static/',  # Archivos estáticos
            '/media/',   # Archivos media
        ]
        
        # Verificar si la URL actual es pública
        is_public = any(request.path.startswith(url) for url in public_urls)
        
        # Si no es pública y no está autenticado, redirigir a login
        if not is_public and not request.session.get('is_authenticated'):
            return redirect('login')
        
        response = self.get_response(request)
        return response
