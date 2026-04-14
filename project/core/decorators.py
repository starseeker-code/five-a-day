"""
Core decorators — reusable access-control decorators.
"""

from functools import wraps

from django.conf import settings
from django.http import Http404


def qa_access_required(view_func):
    """Block access unless DJANGO_ENV=testing, DEBUG=False, and the session
    user matches QA_TESTING_USERNAME.  Returns 404 for everyone else so the
    page appears not to exist."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (
            settings.IS_TESTING_ENV
            and settings.QA_TESTING_USERNAME
            and request.session.get("username") == settings.QA_TESTING_USERNAME
        ):
            raise Http404
        return view_func(request, *args, **kwargs)
    return wrapper
