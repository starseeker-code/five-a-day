"""
Five a Day Django Project

Este archivo asegura que Celery se carga cuando Django arranca.
"""
from .celery import app as celery_app

__all__ = ('celery_app',)
