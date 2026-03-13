from django.contrib import admin
from django.urls import path, include
from core.views import (
    health_check,
    handler400 as h400, handler403 as h403,
    handler404 as h404, handler405 as h405, handler500 as h500,
)

handler400 = h400
handler403 = h403
handler404 = h404
handler405 = h405
handler500 = h500

urlpatterns = [
    path('health/', health_check, name='health_check'),  # Health check para Render
    path('admin/', admin.site.urls),
    path("", include("core.urls"))
]
