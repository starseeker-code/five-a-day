from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.db.models import Sum, Count, Q
from datetime import date, timedelta
import csv
from .models import *

admin.site.site_header = "Five a Day eVolution"
admin.site.site_title = "Five a Day eVolution"
admin.site.index_title = "Five a Day eVolution - Contruyendo un mejor futuro!\nProyecto de las Manitas: Claudia Penelope y Silvia Yubitza"

# Deleted models - commented out to prevent ImportError
# admin.site.register(ExpenseCategory)
# admin.site.register(Expense)
# admin.site.register(RecurringExpenseTemplate)
# admin.site.register(FinancialPeriod)
# admin.site.register(Payroll)

admin.site.register(EnrollmentType)
admin.site.register(Teacher)
admin.site.register(Group)

# Students and parents
class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1  # Number of empty forms to display
    autocomplete_fields = ['parent']

class ParentStudentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    autocomplete_fields = ['student']

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'group', 'active', 'birth_date']
    list_filter = ['group', 'active', 'gdpr_signed']
    search_fields = ['first_name', 'last_name', 'email']
    inlines = [StudentParentInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'birth_date', 'email')
        }),
        ('School Information', {
            'fields': ('school', 'group')
        }),
        ('Health & Preferences', {
            'fields': ('allergies', 'gdpr_signed')
        }),
        ('Status', {
            'fields': ('active', 'withdrawal_date', 'withdrawal_reason')
        }),
    )

@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ['first_name', 'last_name', 'dni', 'phone', 'email']
    search_fields = ['first_name', 'last_name', 'dni', 'email']
    inlines = [ParentStudentInline]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'dni')
        }),
        ('Contact Information', {
            'fields': ('phone', 'email', 'iban')
        }),
    )

@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ['student', 'parent']
    list_filter = ['student__group']
    autocomplete_fields = ['student', 'parent']
    
# Payments and enrollments
@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'student_link', 'parent_link', 'concept', 'amount_display', 
        'payment_method', 'status_display', 'due_date', 'payment_date', 
        'is_overdue_display'
    ]
    list_filter = [
        'payment_status', 'payment_method', 'payment_type', 'currency',
        'due_date', 'payment_date', 'created_at'
    ]
    search_fields = [
        'student__first_name', 'student__last_name',
        'parent__first_name', 'parent__last_name',
        'concept', 'reference_number'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_overdue', 'days_overdue']
    raw_id_fields = ['student', 'parent', 'enrollment']
    
    fieldsets = (
        ('Payment Information', {
            'fields': ('student', 'parent', 'enrollment')
        }),
        ('Payment Details', {
            'fields': (
                'payment_type', 'payment_method', 'amount', 'currency',
                'payment_status', 'concept', 'reference_number'
            )
        }),
        ('Dates', {
            'fields': ('due_date', 'payment_date')
        }),
        ('Additional Information', {
            'fields': ('observations', 'document_url'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at', 'is_overdue', 'days_overdue'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'mark_as_completed', 'mark_as_pending', 'mark_as_failed',
        'soft_delete_payments', 'restore_payments', 'export_to_csv'
    ]
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'student', 'parent', 'enrollment'
        )
    
    def student_link(self, obj):
        if obj.student:
            try:
                app_label = obj.student._meta.app_label
                model_name = obj.student._meta.model_name
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.student.id])
                return format_html('<a href="{}">{}</a>', url, obj.student.full_name)
            except:
                return obj.student.full_name  # Fallback
        return '-'
    student_link.short_description = 'Student'
    student_link.admin_order_field = 'student__last_name'
    
    def parent_link(self, obj):
        if obj.parent:
            try:
                app_label = obj.parent._meta.app_label
                model_name = obj.parent._meta.model_name
                url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.parent.id])
                return format_html('<a href="{}">{}</a>', url, obj.parent.full_name)
            except:
                return obj.parent.full_name
            
        return '-'
    parent_link.short_description = 'Parent'
    parent_link.admin_order_field = 'parent__last_name'
    
    def amount_display(self, obj):
        return format_html('€{} <small>({})</small>', obj.amount, obj.currency)
    amount_display.short_description = 'Amount'
    amount_display.admin_order_field = 'amount'
    
    def status_display(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange' if not obj.is_overdue else 'red',
            'failed': 'red',
            'cancelled': 'gray',
            'refunded': 'blue'
        }
        color = colors.get(obj.payment_status, 'gray')
        
        status_text = obj.get_payment_status_display()
        if obj.is_overdue and obj.payment_status == 'pending':
            status_text += f' ({obj.days_overdue}d overdue)'
            
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color, status_text
        )
    status_display.short_description = 'Status'
    status_display.admin_order_field = 'payment_status'
    
    def is_overdue_display(self, obj):
        return obj.is_overdue
    is_overdue_display.short_description = 'Overdue'
    is_overdue_display.boolean = True
    
    # Admin actions
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(
            payment_status='completed',
            payment_date=date.today()
        )
        self.message_user(request, f'{updated} payments marked as completed.')
    mark_as_completed.short_description = 'Mark selected payments as completed'
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(payment_status='pending')
        self.message_user(request, f'{updated} payments marked as pending.')
    mark_as_pending.short_description = 'Mark selected payments as pending'
    
    def mark_as_failed(self, request, queryset):
        updated = queryset.update(payment_status='failed')
        self.message_user(request, f'{updated} payments marked as failed.')
    mark_as_failed.short_description = 'Mark selected payments as failed'
    
    def soft_delete_payments(self, request, queryset):
        updated = queryset.update(active=False)
        self.message_user(request, f'{updated} payments deactivated (soft deleted).')
    soft_delete_payments.short_description = 'Deactivate selected payments'
    
    def restore_payments(self, request, queryset):
        updated = queryset.update(active=True)
        self.message_user(request, f'{updated} payments restored.')
    restore_payments.short_description = 'Restore selected payments'
    
    def export_to_csv(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="payments.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'ID', 'Student', 'Parent', 'Concept', 'Amount', 'Currency',
            'Payment Method', 'Status', 'Due Date', 'Payment Date',
            'Reference', 'Created'
        ])
        
        for payment in queryset:
            writer.writerow([
                payment.id,
                payment.student.full_name if payment.student else '',
                payment.parent.full_name if payment.parent else '',
                payment.concept,
                payment.amount,
                payment.currency,
                payment.get_payment_method_display(),
                payment.get_payment_status_display(),
                payment.due_date.strftime('%Y-%m-%d') if payment.due_date else '',
                payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
                payment.reference_number,
                payment.created_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    export_to_csv.short_description = 'Export selected payments to CSV'

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'student', 'enrollment_type', 'schedule_type', 'status',
        'enrollment_period_start', 'enrollment_period_end', 
        'final_amount', 'is_paid_display'
    ]
    list_filter = [
        'status', 'schedule_type', 'enrollment_type',
        'enrollment_period_start', 'enrollment_date'
    ]
    search_fields = [
        'student__first_name', 'student__last_name',
        'notes'
    ]
    readonly_fields = ['created_at', 'updated_at', 'is_paid', 'remaining_amount']
    raw_id_fields = ['student']
    
    fieldsets = (
        ('Student Information', {
            'fields': ('student',)
        }),
        ('Enrollment Details', {
            'fields': (
                'enrollment_type', 'schedule_type', 'status',
                'enrollment_period_start', 'enrollment_period_end',
                'enrollment_date'
            )
        }),
        ('Pricing', {
            'fields': (
                'enrollment_amount', 'discount_percentage', 'final_amount'
            )
        }),
        ('Additional Information', {
            'fields': ('document_url', 'notes'),
            'classes': ('collapse',)
        }),
        ('System Information', {
            'fields': ('is_paid', 'remaining_amount', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def is_paid_display(self, obj):
        if obj.is_paid:
            return True  # TODO: Still testing!
            return format_html('<span style="color: green;">✓ Paid</span>')
        else:
            return False  # TODO: Still testing!
            remaining = obj.remaining_amount
            return format_html(
                '<span style="color: red;">✗ Pending (€{})</span>',
                remaining
            )
    is_paid_display.short_description = 'Payment Status'
    is_paid_display.boolean = True
