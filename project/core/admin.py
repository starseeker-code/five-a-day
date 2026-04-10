from django.contrib import admin
from .models import HistoryLog, TodoItem, ScheduleSlot, FunFridayAttendance

admin.site.site_header = "Five a Day eVolution"
admin.site.site_title = "Five a Day eVolution"
admin.site.index_title = "Five a Day eVolution - Construyendo un mejor futuro!"


@admin.register(HistoryLog)
class HistoryLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'message', 'icon', 'created_at')
    list_filter = ('action',)
    ordering = ('-created_at',)
    readonly_fields = ('action', 'message', 'icon', 'created_at')


@admin.register(TodoItem)
class TodoItemAdmin(admin.ModelAdmin):
    list_display = ('text', 'due_date', 'is_overdue', 'created_at')
    list_filter = ('due_date',)
    ordering = ('due_date',)


@admin.register(ScheduleSlot)
class ScheduleSlotAdmin(admin.ModelAdmin):
    list_display = ('row', 'day', 'col', 'group')
    list_filter = ('day', 'group')
    ordering = ('row', 'day', 'col')


@admin.register(FunFridayAttendance)
class FunFridayAttendanceAdmin(admin.ModelAdmin):
    list_display = ('student', 'date', 'created_at')
    list_filter = ('date',)
    ordering = ('-date',)
    raw_id_fields = ('student',)
