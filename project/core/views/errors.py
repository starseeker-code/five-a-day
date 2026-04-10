from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt


def handler400(request, exception=None):
    return render(request, "400.html", status=400)


def handler403(request, exception=None):
    return render(request, "403.html", status=403)


def handler404(request, exception=None):
    return render(request, "404.html", status=404)


def handler405(request, exception=None):
    return render(request, "405.html", status=405)


def handler500(request):
    return render(request, "500.html", status=500)


def test_error_400(request):
    return render(request, "400.html", status=400)


def test_error_403(request):
    return render(request, "403.html", status=403)


def test_error_404(request):
    return render(request, "404.html", status=404)


def test_error_405(request):
    return render(request, "405.html", status=405)


def test_error_500(request):
    return render(request, "500.html", status=500)


@csrf_exempt
def health_check(request):
    return JsonResponse(
        {
            "status": "healthy",
            "service": "fiveaday",
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        },
        status=200,
    )
