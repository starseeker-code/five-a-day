from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpRequest, HttpResponse

def test_view(request):
    return  HttpResponse("Hello, world!")

class TestView(View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(f"Hello, World!\nArgs: {args}\nKwargs: {kwargs}\nRequest: {request}")