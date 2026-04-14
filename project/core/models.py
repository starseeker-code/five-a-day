"""
Core models — lightweight cross-cutting models that don't belong to a specific domain.
Domain models live in students/ and billing/.
"""

from datetime import date, timedelta

from django.db import models
from django.utils import timezone


class ScheduleSlot(models.Model):
    """Persists which group is assigned to each schedule slot (row, day, col)."""

    row = models.IntegerField()  # 0, 1, 2
    day = models.IntegerField()  # 0=Mon … 4=Fri
    col = models.IntegerField()  # 0 or 1
    group = models.ForeignKey(
        "students.Group", null=True, blank=True, on_delete=models.SET_NULL, related_name="schedule_slots"
    )

    class Meta:
        db_table = "schedule_slots"
        constraints = [
            models.UniqueConstraint(fields=["row", "day", "col"], name="unique_schedule_slot"),
        ]
        ordering = ["row", "day", "col"]

    def __str__(self):
        return f"Slot row={self.row} day={self.day} col={self.col}"


class FunFridayAttendance(models.Model):
    """Tracks which Fridays a student attended (or is registered for) Fun Friday."""

    student = models.ForeignKey("students.Student", on_delete=models.CASCADE, related_name="fun_friday_dates")
    date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "fun_friday_attendance"
        constraints = [
            models.UniqueConstraint(fields=["student", "date"], name="unique_fun_friday_attendance"),
        ]
        ordering = ["-date"]

    def __str__(self):
        return f"{self.student} - {self.date}"


class TodoItem(models.Model):
    text = models.CharField(max_length=500)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "todo_items"
        ordering = ["due_date", "created_at"]

    def __str__(self):
        return f"{self.text} ({self.due_date})"

    @property
    def is_overdue(self):
        return self.due_date < date.today()


class HistoryLog(models.Model):
    """Stores up to 1000 history log entries for user actions."""

    ACTION_CHOICES = [
        ("todo_completed", "Tarea completada"),
        ("payment_completed", "Pago completado"),
        ("student_enrolled", "Alumno matriculado"),
        ("teacher_created", "Profesor creado"),
        ("group_created", "Grupo creado"),
        ("group_updated", "Grupo actualizado"),
        ("config_updated", "Configuración actualizada"),
        ("payment_created", "Pago creado"),
        ("email_sent", "Email enviado"),
        ("schedule_updated", "Horario actualizado"),
    ]

    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    message = models.CharField(max_length=300)
    icon = models.CharField(max_length=40, default="history")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "history_logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_action_display()}] {self.message}"

    MAX_ENTRIES = 1000

    @classmethod
    def log(cls, action, message, icon="history"):
        """Create a history entry, enforcing the 1000-record cap."""
        entry = cls.objects.create(action=action, message=message, icon=icon)
        if cls.objects.count() > cls.MAX_ENTRIES:
            keep_ids = cls.objects.order_by("-created_at").values_list("id", flat=True)[: cls.MAX_ENTRIES]
            cls.objects.exclude(id__in=keep_ids).delete()
        return entry

    @classmethod
    def log_debounced(cls, action, message, icon="history", minutes=5):
        """Create a history entry only if no entry with the same action
        exists within the last `minutes` minutes."""
        cutoff = timezone.now() - timedelta(minutes=minutes)
        if cls.objects.filter(action=action, created_at__gte=cutoff).exists():
            return None
        return cls.log(action, message, icon=icon)
