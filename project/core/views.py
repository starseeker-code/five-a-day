from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.http import HttpRequest, HttpResponse
from .models import *
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse

def home(request):
    return render(request, "home.html")

def all_info(request):
    context = {}
    return render(request, "database.html", context)

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


def students(request):
    """
    Students list view - displays all students and handles create/update operations
    """
    if request.method == 'POST':
        return handle_student_form(request)
    
    # Get all students with related data
    students = Student.objects.select_related('group', 'group__teacher').prefetch_related('parents').filter(active=True)
    
    # Get all groups and parents for the form
    groups = Group.objects.filter(active=True).select_related('teacher')
    parents = Parent.objects.all()
    
    context = {
        'students': students,
        'groups': groups,
        'parents': parents,
    }
    
    return render(request, 'students.html', context)

def handle_student_form(request):
    """
    Handle student creation and updates
    """
    try:
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        birth_date = request.POST.get('birth_date')
        email = request.POST.get('email', '').strip()
        school = request.POST.get('school', '').strip()
        group_id = request.POST.get('group')
        allergies = request.POST.get('allergies', '').strip()
        gdpr_signed = request.POST.get('gdpr_signed') == 'on'
        active = request.POST.get('active') == 'on'
        parent_ids = request.POST.getlist('parents')
        
        # Validation
        if not first_name or not last_name:
            messages.error(request, 'El nombre y apellidos son obligatorios.')
            return redirect('students')
        
        if not birth_date:
            messages.error(request, 'La fecha de nacimiento es obligatoria.')
            return redirect('students')
            
        if not group_id:
            messages.error(request, 'Debe seleccionar un grupo.')
            return redirect('students')
            
        if not parent_ids:
            messages.error(request, 'Debe seleccionar al menos un padre/tutor.')
            return redirect('students')
        
        # Get the group
        try:
            group = Group.objects.get(id=group_id, active=True)
        except Group.DoesNotExist:
            messages.error(request, 'El grupo seleccionado no existe.')
            return redirect('students')
        
        # Get parents
        parents = Parent.objects.filter(id__in=parent_ids)
        if len(parents) != len(parent_ids):
            messages.error(request, 'Algunos padres seleccionados no existen.')
            return redirect('students')
        
        # Use transaction to ensure data consistency
        with transaction.atomic():
            # Check if this is an update (student_id present) or create
            student_id = request.POST.get('student_id')
            
            if student_id:  # Update existing student
                try:
                    student = Student.objects.get(id=student_id)
                    
                    # Update student fields
                    student.first_name = first_name
                    student.last_name = last_name
                    student.birth_date = birth_date
                    student.email = email if email else ''
                    student.school = school if school else ''
                    student.group = group
                    student.allergies = allergies if allergies else ''
                    student.gdpr_signed = gdpr_signed
                    student.active = active
                    
                    student.full_clean()  # Validate the model
                    student.save()
                    
                    # Update parent relationships
                    student.parents.clear()  # Remove all current relationships
                    student.parents.set(parents)  # Set new relationships
                    
                    messages.success(request, f'Estudiante {student.full_name} actualizado correctamente.')
                    
                except Student.DoesNotExist:
                    messages.error(request, 'El estudiante a actualizar no existe.')
                    return redirect('students')
                    
            else:  # Create new student
                student = Student(
                    first_name=first_name,
                    last_name=last_name,
                    birth_date=birth_date,
                    email=email if email else '',
                    school=school if school else '',
                    group=group,
                    allergies=allergies if allergies else '',
                    gdpr_signed=gdpr_signed,
                    active=active
                )
                
                student.full_clean()  # Validate the model
                student.save()
                
                # Add parent relationships
                student.parents.set(parents)
                
                messages.success(request, f'Estudiante {student.full_name} creado correctamente.')
        
        return redirect('students')
        
    except ValidationError as e:
        if hasattr(e, 'message_dict'):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        else:
            messages.error(request, f'Error de validación: {e.message}')
        return redirect('students')
        
    except Exception as e:
        messages.error(request, f'Error al procesar el formulario: {str(e)}')
        return redirect('students')

def student_detail(request, student_id):
    """
    API endpoint to get student details for editing
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        student = get_object_or_404(
            Student.objects.select_related('group').prefetch_related('parents'), 
            id=student_id
        )
        
        # Prepare student data
        student_data = {
            'id': student.id,
            'first_name': student.first_name,
            'last_name': student.last_name,
            'birth_date': student.birth_date.strftime('%Y-%m-%d'),
            'email': student.email,
            'school': student.school,
            'group': student.group.id,
            'allergies': student.allergies,
            'gdpr_signed': student.gdpr_signed,
            'active': student.active,
            'parents': [parent.id for parent in student.parents.all()]
        }
        
        return JsonResponse(student_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def update_student(request, student_id):
    """
    Maneja la edición de un estudiante:
    - GET: devuelve datos en JSON para rellenar el modal (AJAX).
    - POST: actualiza datos usando handle_student_form y redirige a /students.
    """
    if request.method == 'GET':
        student = get_object_or_404(
            Student.objects.select_related('group').prefetch_related('parents'),
            id=student_id
        )

        data = {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "birth_date": student.birth_date.strftime("%Y-%m-%d"),
            "email": student.email,
            "school": student.school,
            "group": student.group.id if student.group else None,
            "allergies": student.allergies,
            "gdpr_signed": student.gdpr_signed,
            "active": student.active,
            "parents": list(student.parents.values_list("id", flat=True)),
        }
        return JsonResponse(data)

    elif request.method == 'POST':
        request.POST = request.POST.copy()
        request.POST['student_id'] = student_id
        return handle_student_form(request)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


