from django.contrib import admin
from django.urls import include, path

from core.views import (
    handler400 as h400,
)
from core.views import (
    handler403 as h403,
)
from core.views import (
    handler404 as h404,
)
from core.views import (
    handler405 as h405,
)
from core.views import (
    handler500 as h500,
)
from core.views import (
    health_check,
)

handler400 = h400
handler403 = h403
handler404 = h404
handler405 = h405
handler500 = h500

urlpatterns = [
    path("health/", health_check, name="health_check"),
    path("admin/", admin.site.urls),
    path("", include("students.urls")),
    path("", include("billing.urls")),
    path("", include("comms.urls")),
    path("", include("core.urls")),
]
