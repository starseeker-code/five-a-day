"""
Configuración de Celery para Five a Day
https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html
"""

import os

from celery import Celery
from celery.schedules import crontab

# Establecer el módulo de configuración de Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

app = Celery("fiveaday")

# Usar configuración de Django con prefijo CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodescubrir tareas en todas las apps instaladas
app.autodiscover_tasks()


# ============================================================================
# CELERY BEAT SCHEDULE - Tareas programadas
# ============================================================================
app.conf.beat_schedule = {
    # Birthday emails — daily at 8:00 AM (Europe/Madrid)
    "send-birthday-emails-daily": {
        "task": "comms.tasks.send_birthday_emails_task",
        "schedule": crontab(hour=8, minute=0),
        "options": {"queue": "emails"},
    },
    # Payment reminders — every Monday at 9:00 AM
    "send-payment-reminders-weekly": {
        "task": "comms.tasks.send_payment_reminders",
        "schedule": crontab(hour=9, minute=0, day_of_week=1),
        "options": {"queue": "emails"},
    },
}

app.conf.timezone = "Europe/Madrid"


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tarea de debug para verificar que Celery funciona"""
    print(f"Request: {self.request!r}")
