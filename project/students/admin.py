from django.contrib import admin

from students.models import Group, Parent, Student, StudentParent, Teacher

admin.site.register(Teacher)
admin.site.register(Group)


# Students and parents
class StudentParentInline(admin.TabularInline):
    model = StudentParent
    extra = 1  # Number of empty forms to display
    autocomplete_fields = ["parent"]


class ParentStudentInline(admin.TabularInline):
    model = StudentParent
    extra = 1
    autocomplete_fields = ["student"]


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "group", "active", "birth_date"]
    list_filter = ["group", "active", "gdpr_signed"]
    search_fields = ["first_name", "last_name"]
    inlines = [StudentParentInline]

    fieldsets = (
        ("Personal Information", {"fields": ("first_name", "last_name", "birth_date")}),
        ("School Information", {"fields": ("school", "group")}),
        ("Health & Preferences", {"fields": ("allergies", "gdpr_signed")}),
        ("Status", {"fields": ("active", "withdrawal_date", "withdrawal_reason")}),
    )


@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
    list_display = ["first_name", "last_name", "dni", "phone", "email"]
    search_fields = ["first_name", "last_name", "dni", "email"]
    inlines = [ParentStudentInline]

    fieldsets = (
        ("Personal Information", {"fields": ("first_name", "last_name", "dni")}),
        ("Contact Information", {"fields": ("phone", "email", "iban")}),
    )


@admin.register(StudentParent)
class StudentParentAdmin(admin.ModelAdmin):
    list_display = ["student", "parent"]
    list_filter = ["student__group"]
    autocomplete_fields = ["student", "parent"]
