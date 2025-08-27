from django.contrib import admin
from .models import *

admin.site.register(ExpenseCategory)
admin.site.register(Expense)
admin.site.register(RecurringExpenseTemplate)
admin.site.register(FinancialPeriod)
admin.site.register(EnrollmentType)
admin.site.register(Enrollment)
admin.site.register(Payment)
admin.site.register(Payroll)
admin.site.register(Teacher)
admin.site.register(Group)
admin.site.register(Student)
admin.site.register(Parent)
admin.site.register(StudentParent)
