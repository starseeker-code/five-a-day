from django.urls import path
from core.views import *

urlpatterns = [
    path("", test_view, name="test"),  # type: ignore
    path("test/", TestView.as_view(), name="test-class")
]
