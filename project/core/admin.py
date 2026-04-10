from django.contrib import admin
from .models import HistoryLog

admin.site.site_header = "Five a Day eVolution"
admin.site.site_title = "Five a Day eVolution"
admin.site.index_title = "Five a Day eVolution - Construyendo un mejor futuro!"


@admin.register(HistoryLog)
class HistoryLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'message', 'icon', 'created_at')
    list_filter = ('action',)
    ordering = ('-created_at',)
    readonly_fields = ('action', 'message', 'icon', 'created_at')
