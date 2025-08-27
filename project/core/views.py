from django.shortcuts import render, get_object_or_404
from django.views import View
from django.http import HttpRequest, HttpResponse
from .models import *

def test_view(request):
    return  HttpResponse("This is the home page")

# ---------- Expense & Finance ----------
def expense_categories(request):
    categories = ExpenseCategory.objects.all()
    return render(request, "expense_categories.html", {"categories": categories})

def expenses(request):
    expenses = Expense.objects.all()
    return render(request, "expenses.html", {"expenses": expenses})

def recurring_expense_templates(request):
    templates = RecurringExpenseTemplate.objects.all()
    return render(request, "recurring_expense_templates.html", {"templates": templates})

def financial_periods(request):
    periods = FinancialPeriod.objects.all()
    return render(request, "financial_periods.html", {"periods": periods})


# ---------- Enrollment ----------
def enrollment_types(request):
    types = EnrollmentType.objects.all()
    return render(request, "enrollment_types.html", {"types": types})

def enrollments(request):
    enrollments = Enrollment.objects.all()
    return render(request, "enrollments.html", {"enrollments": enrollments})


# ---------- Payments ----------
def payments(request):
    payments = Payment.objects.all()
    return render(request, "payments.html", {"payments": payments})


# ---------- Payroll ----------
def payrolls(request):
    payrolls = Payroll.objects.all()
    return render(request, "payrolls.html", {"payrolls": payrolls})


# ---------- People ----------
def teachers(request):
    teachers = Teacher.objects.all()
    return render(request, "teachers.html", {"teachers": teachers})

def groups(request):
    groups = Group.objects.all()
    return render(request, "groups.html", {"groups": groups})

def students(request):
    students = Student.objects.all()
    return render(request, "students.html", {"students": students})

def parents(request):
    parents = Parent.objects.all()
    return render(request, "parents.html", {"parents": parents})
