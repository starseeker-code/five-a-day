from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
#from django.views import View
from django.views.generic import FormView, DetailView, ListView, UpdateView, CreateView
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from .models import *
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.views.decorators.http import require_http_methods
from django.urls import reverse_lazy
from decimal import Decimal
import json
from datetime import date
from core.transactions import all_students, all_payments
from core.forms import StudentForm, ParentForm, EnrollmentForm, ParentFormSet
from core.email import email_service
from django.conf import settings
import os

def login_view(request):
    """Vista de login con credenciales desde .env"""
    # Si ya está autenticado, redirigir al home
    if request.session.get('is_authenticated'):
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        # Validar contra credenciales en .env
        valid_username = os.getenv('LOGIN_USERNAME', 'fiveaday')
        valid_password = os.getenv('LOGIN_PASSWORD', 'Fiveaday123!')
        
        if username == valid_username and password == valid_password:
            # Autenticación exitosa
            request.session['is_authenticated'] = True
            request.session['username'] = username
            messages.success(request, f'¡Bienvenido {username}!')
            return redirect('home')
        else:
            # Credenciales incorrectas
            messages.error(request, '❌ Usuario o contraseña incorrectos')
    
    return render(request, 'login.html')

def logout_view(request):
    """Vista de logout"""
    request.session.flush()  # Eliminar toda la sesión
    messages.success(request, '✅ Has cerrado sesión correctamente')
    return redirect('login')

def home(request):
    return render(request, "home.html")

def all_info(request):
    return render(request, "all_info.html", {"students": all_students, "payments": all_payments})

def email_test(request):
    """Vista para probar el envío de emails usando el servicio genérico"""
    if request.method == 'GET':
        try:
            # Usar el servicio genérico de emails
            success = email_service.send_email(
                template_name='happy_birthday',
                recipients=settings.EMAIL_HOST_USER,
                subject='🎉 ¡Feliz Cumpleaños! - Five a Day (Prueba)',
                context={'name': 'Estudiante de Prueba'}
            )
            
            if success:
                messages.success(request, f'✅ Email enviado correctamente a {settings.EMAIL_HOST_USER}')
            else:
                messages.error(request, '❌ Error al enviar email. Verifica la configuración SMTP.')
            
            return render(request, 'emails/happy_birthday.html', {
                'name': 'Estudiante de Prueba',
                'year': 2025
            })
            
        except Exception as e:
            messages.error(request, f'❌ Error: {str(e)}')
            return render(request, 'emails/happy_birthday.html', {
                'name': 'Estudiante de Prueba',
                'year': 2025,
                'error': str(e)
            })
    
    return render(request, 'emails/happy_birthday.html', {
        'name': 'Estudiante de Prueba',
        'year': 2025
    })

# ---> Estudiantes | Pagos || DASHBOARDS (Home + Info) | Aplicaciones | Facturacion | UI! || Gastos | Renta | UI!! || Configuracion | Contacto y ayuda
# TESTING CODE ("testing/")

class StudentsView(CreateView):
    model = Student
    form_class = StudentForm
    template_name = 'student_create.html'

    success_url = reverse_lazy('student_create')  # TODO: Volver al mismo lugar para crear

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'parent_form' not in context:
            context['parent_form'] = ParentForm(self.request.POST or None)
        if 'enrollment_form' not in context:
            context['enrollment_form'] = EnrollmentForm(self.request.POST or None)
        return context

    def form_valid(self, form):
        parent_form = ParentForm(self.request.POST)
        enrollment_form = EnrollmentForm(self.request.POST)
        if not (parent_form.is_valid() and enrollment_form.is_valid()):
            return self.form_invalid(form)
        try:
            with transaction.atomic():
                parent_dni = parent_form.cleaned_data.get('dni')
                if parent_dni:
                    parent_dni = parent_dni.strip().upper()
                parent, created = Parent.objects.get_or_create(
                    dni=parent_dni,
                    defaults={
                        'first_name': parent_form.cleaned_data.get('first_name'),
                        'last_name': parent_form.cleaned_data.get('last_name'),
                        'phone': parent_form.cleaned_data.get('phone'),
                        'email': parent_form.cleaned_data.get('email'),
                        'iban': parent_form.cleaned_data.get('iban', '') or '',
                    }
                )
                if not created:
                    for field in ('first_name', 'last_name', 'phone', 'email', 'iban'):
                        val = parent_form.cleaned_data.get(field)
                        if val is not None:
                            setattr(parent, field, val)
                    parent.save()
                self.object = form.save()
                self.object.parents.add(parent)
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = self.object
                enrollment.save()
                messages.success(
                    self.request,
                    f'¡Estudiante {self.object.full_name} creado exitosamente!'
                )

        except Exception as e:
            messages.error(self.request, f'Error al crear el estudiante: {str(e)}')
            return self.form_invalid(form)

        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form):
        context = self.get_context_data(form=form)

        context['parent_form'] = ParentForm(self.request.POST or None)
        context['enrollment_form'] = EnrollmentForm(self.request.POST or None)
        return self.render_to_response(context)


# ============================================================================
# PARENT AND STUDENT MANAGEMENT - Parent-First Flow
# ============================================================================

class ParentCreateView(CreateView):
    """Vista para crear un nuevo padre/tutor"""
    model = Parent
    form_class = ParentForm
    template_name = 'parent_create.html'
    
    def get_success_url(self):
        # Después de crear el padre, redirigir a crear estudiante con el parent_id
        return reverse_lazy('student_create') + f'?parent_id={self.object.id}'
    
    def form_valid(self, form):
        try:
            # Verificar si ya existe un padre con ese DNI
            dni = form.cleaned_data.get('dni')
            existing_parent = Parent.objects.filter(dni=dni).first()
            
            if existing_parent:
                messages.info(
                    self.request,
                    f'El padre/tutor {existing_parent.full_name} ya existe. '
                    f'Serás redirigido para crear un estudiante.'
                )
                self.object = existing_parent
                return HttpResponseRedirect(self.get_success_url())
            
            # Si no existe, crear el nuevo padre
            self.object = form.save()
            messages.success(
                self.request,
                f'Padre/tutor {self.object.full_name} creado exitosamente. '
                f'Ahora crea un estudiante para este padre.'
            )
            return HttpResponseRedirect(self.get_success_url())
            
        except Exception as e:
            messages.error(self.request, f'Error al crear el padre: {str(e)}')
            return self.form_invalid(form)


class StudentCreateView(CreateView):
    """
    Vista para crear un nuevo estudiante.
    Puede recibir un parent_id como parámetro GET para pre-vincular al padre.
    """
    model = Student
    form_class = StudentForm
    template_name = 'student_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el parent_id de los parámetros GET si existe
        parent_id = self.request.GET.get('parent_id')
        
        if parent_id:
            try:
                parent = Parent.objects.get(id=parent_id)
                context['parent'] = parent
                context['parent_id'] = parent_id
            except Parent.DoesNotExist:
                messages.error(self.request, 'El padre especificado no existe')
        
        # Agregar el formulario de matrícula
        if 'enrollment_form' not in context:
            context['enrollment_form'] = EnrollmentForm(self.request.POST or None)
        
        # Agregar grupos disponibles
        context['groups'] = Group.objects.filter(active=True)
        
        return context
    
    def form_valid(self, form):
        enrollment_form = EnrollmentForm(self.request.POST)
        
        if not enrollment_form.is_valid():
            return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                # Crear el estudiante
                student = form.save()
                
                # Obtener el parent_id del POST o GET
                parent_id = self.request.POST.get('parent_id') or self.request.GET.get('parent_id')
                
                if not parent_id:
                    messages.error(self.request, 'Debe especificar un padre para el estudiante')
                    student.delete()
                    return self.form_invalid(form)
                
                # Vincular al padre
                try:
                    parent = Parent.objects.get(id=parent_id)
                    student.parents.add(parent)
                except Parent.DoesNotExist:
                    messages.error(self.request, 'El padre especificado no existe')
                    student.delete()
                    return self.form_invalid(form)
                
                # Crear la matrícula
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = student
                enrollment.save()
                
                messages.success(
                    self.request,
                    f'¡Estudiante {student.full_name} creado exitosamente!'
                )
                
                # Verificar si el usuario quiere crear otro hermano
                if 'create_sibling' in self.request.POST:
                    # Redirigir a crear otro estudiante con el mismo padre
                    return HttpResponseRedirect(
                        reverse_lazy('student_create') + f'?parent_id={parent_id}'
                    )
                else:
                    # Redirigir a la lista de estudiantes
                    return HttpResponseRedirect(reverse_lazy('students_list'))
                
        except Exception as e:
            messages.error(self.request, f'Error al crear el estudiante: {str(e)}')
            return self.form_invalid(form)
    
    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        context['enrollment_form'] = EnrollmentForm(self.request.POST)
        return self.render_to_response(context)


class StudentListView(ListView):
    """Vista para listar todos los estudiantes"""
    model = Student
    template_name = 'students.html'
    context_object_name = 'students'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Student.objects.filter(active=True).select_related('group').prefetch_related('parents')
        
        # Búsqueda opcional
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )
        
        return queryset.order_by('last_name', 'first_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('search', '')
        context['groups'] = Group.objects.filter(active=True)
        context['parents'] = Parent.objects.all()
        return context


class StudentUpdateView(UpdateView):
    """Vista para actualizar un estudiante existente"""
    model = Student
    form_class = StudentForm
    template_name = 'student_update.html'
    pk_url_kwarg = 'student_id'
    
    def get_success_url(self):
        return reverse_lazy('students_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener la matrícula activa
        try:
            enrollment = self.object.enrollments.filter(status='active').latest('created_at')
        except Enrollment.DoesNotExist:
            enrollment = None
        
        if 'enrollment_form' not in context:
            context['enrollment_form'] = EnrollmentForm(
                self.request.POST or None,
                instance=enrollment
            )
        
        context['parents'] = self.object.parents.all()
        context['groups'] = Group.objects.filter(active=True)
        
        return context
    
    def form_valid(self, form):
        try:
            enrollment = self.object.enrollments.filter(status='active').latest('created_at')
        except Enrollment.DoesNotExist:
            enrollment = None
        
        enrollment_form = EnrollmentForm(self.request.POST, instance=enrollment)
        
        if not enrollment_form.is_valid():
            return self.form_invalid(form)
        
        try:
            with transaction.atomic():
                student = form.save()
                
                enrollment = enrollment_form.save(commit=False)
                enrollment.student = student
                enrollment.save()
                
                messages.success(self.request, f'Estudiante {student.full_name} actualizado exitosamente')
                
        except Exception as e:
            messages.error(self.request, f'Error al actualizar el estudiante: {str(e)}')
            return self.form_invalid(form)
        
        return HttpResponseRedirect(self.get_success_url())
    
    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        try:
            enrollment = self.object.enrollments.filter(status='active').latest('created_at')
        except Enrollment.DoesNotExist:
            enrollment = None
        context['enrollment_form'] = EnrollmentForm(self.request.POST, instance=enrollment)
        return self.render_to_response(context)


class StudentDetailView(DetailView):
    """Vista para ver detalles de un estudiante"""
    model = Student
    template_name = 'student_detail.html'
    context_object_name = 'student'
    pk_url_kwarg = 'student_id'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parents'] = self.object.parents.all()
        context['enrollments'] = self.object.enrollments.all().order_by('-created_at')
        context['payments'] = Payment.objects.filter(student=self.object).order_by('-payment_date')
        return context


# ============================================================================
# PAYMENT SEARCH AND HELPER APIs (keeping for compatibility)
# ============================================================================

def search_students(request):
    
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
            return redirect('students_list')
        
        if not birth_date:
            messages.error(request, 'La fecha de nacimiento es obligatoria.')
            return redirect('students_list')
            
        if not group_id:
            messages.error(request, 'Debe seleccionar un grupo.')
            return redirect('students_list')
            
        if not parent_ids:
            messages.error(request, 'Debe seleccionar al menos un padre/tutor.')
            return redirect('students_list')
        
        # Get the group
        try:
            group = Group.objects.get(id=group_id, active=True)
        except Group.DoesNotExist:
            messages.error(request, 'El grupo seleccionado no existe.')
            return redirect('students_list')
        
        # Get parents
        parents = Parent.objects.filter(id__in=parent_ids)
        if len(parents) != len(parent_ids):
            messages.error(request, 'Algunos padres seleccionados no existen.')
            return redirect('students_list')
        
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
                    return redirect('students_list')
                    
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
        
        return redirect('students_list')
        
    except ValidationError as e:
        if hasattr(e, 'message_dict'):
            for field, errors in e.message_dict.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
        else:
            messages.error(request, f'Error de validación: {e.message}')
        return redirect('students_list')
        
    except Exception as e:
        messages.error(request, f'Error al procesar el formulario: {str(e)}')
        return redirect('students_list')

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



def payments_list(request):
    """
    Main payments list view with pagination
    Shows active payments only (not deactivated ones)
    """
    # Get all active payments ordered by most recent first
    payments_queryset = Payment.objects.select_related('student', 'parent', 'enrollment').order_by('-created_at', '-due_date')
    
    # Add search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        payments_queryset = payments_queryset.filter(
            Q(student__first_name__icontains=search_query) |
            Q(student__last_name__icontains=search_query) |
            Q(parent__first_name__icontains=search_query) |
            Q(parent__last_name__icontains=search_query) |
            Q(concept__icontains=search_query) |
            Q(reference_number__icontains=search_query)
        )
    
    # Pagination - 10 payments per page, max 100 total
    paginator = Paginator(payments_queryset[:100], 10)
    page_number = request.GET.get('page', 1)
    payments = paginator.get_page(page_number)
    
    context = {
        'payments': payments,
        'search_query': search_query,
    }
    
    return render(request, 'payments/payments_list.html', context)

@require_http_methods(["GET", "POST"])
def create_payment(request):
    """
    Create new payment
    """
    if request.method == 'POST':
        try:
            # Get form data
            student_id = request.POST.get('student_id')
            parent_id = request.POST.get('parent_id')
            
            # Validate student and parent exist
            student = get_object_or_404(Student, id=student_id)
            parent = get_object_or_404(Parent, id=parent_id)
            
            # Validate relationship
            if not student.parents.filter(id=parent_id).exists():
                messages.error(request, 'El padre/tutor seleccionado no está asociado con este estudiante.')
                return redirect('payments_list')
            
            # Get enrollment if exists
            enrollment = student.enrollments.first()
            
            # Create payment
            print("Se crea pago")
            payment = Payment.objects.create(
                student=student,
                parent=parent,
                enrollment=enrollment,
                payment_type=request.POST.get('payment_type'),
                payment_method=request.POST.get('payment_method'),
                amount=Decimal(request.POST.get('amount')),
                currency=request.POST.get('currency', 'EUR'),
                payment_status=request.POST.get('payment_status', 'pending'),
                due_date=request.POST.get('due_date'),
                payment_date=request.POST.get('payment_date') or None,
                concept=request.POST.get('concept'),
                reference_number=request.POST.get('reference_number', ''),
                observations=request.POST.get('observations', '')
            )
            print("Terminado de crear pago")
            messages.success(request, f'Pago creado exitosamente para {student.full_name}.')
            print("Se redirecciona!")
            return redirect('payments_list')
            
        except Exception as e:
            messages.error(request, f'Error al crear el pago: {str(e)}')
            return redirect('payments_list')
    
    return redirect('payments_list')

def payment_detail(request, payment_id):
    """
    Get payment details as JSON for editing
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    data = {
        'id': payment.id,
        'student': {
            'id': payment.student.id,
            'full_name': payment.student.full_name,
            'school': payment.student.school or ''
        },
        'parent': {
            'id': payment.parent.id,
            'full_name': payment.parent.full_name,
            'email': payment.parent.email
        },
        'enrollment': {
            'id': payment.enrollment.id if payment.enrollment else None,
            'enrollment_type': payment.enrollment.enrollment_type.display_name if payment.enrollment else None
        } if payment.enrollment else None,
        'payment_type': payment.payment_type,
        'payment_method': payment.payment_method,
        'amount': str(payment.amount),
        'currency': payment.currency,
        'payment_status': payment.payment_status,
        'due_date': payment.due_date.isoformat() if payment.due_date else None,
        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
        'concept': payment.concept,
        'reference_number': payment.reference_number,
        'observations': payment.observations,
        'is_overdue': payment.is_overdue,
        'days_overdue': payment.days_overdue if payment.is_overdue else 0
    }
    
    return JsonResponse(data)

@require_http_methods(["POST"])
def update_payment(request, payment_id):
    """
    Update existing payment
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    try:
        # Get form data
        student_id = request.POST.get('student_id')
        parent_id = request.POST.get('parent_id')
        
        # Validate student and parent exist
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)
        
        # Validate relationship
        if not student.parents.filter(id=parent_id).exists():
            messages.error(request, 'El padre/tutor seleccionado no está asociado con este estudiante.')
            return redirect('payments_list')
        
        # Update payment fields
        payment.student = student
        payment.parent = parent
        payment.payment_type = request.POST.get('payment_type')
        payment.payment_method = request.POST.get('payment_method')
        payment.amount = Decimal(request.POST.get('amount'))
        payment.currency = request.POST.get('currency', 'EUR')
        payment.payment_status = request.POST.get('payment_status')
        payment.due_date = request.POST.get('due_date')
        payment.payment_date = request.POST.get('payment_date') or None
        payment.concept = request.POST.get('concept')
        payment.reference_number = request.POST.get('reference_number', '')
        payment.observations = request.POST.get('observations', '')
        
        payment.save()
        
        messages.success(request, f'Pago actualizado exitosamente para {student.full_name}.')
        
    except Exception as e:
        messages.error(request, f'Error al actualizar el pago: {str(e)}')
    
    return redirect('payments_list')

def payment_detail_view(request, payment_id):
    """
    Detailed view of a payment (read-only)
    """
    payment = get_object_or_404(Payment, id=payment_id)
    
    context = {
        'payment': payment,
    }
    
    return render(request, 'payments/payment_detail.html', context)

# Soft delete!
@require_http_methods(["POST"])
def deactivate_payment(request, payment_id):
    """
    Soft delete - deactivate payment instead of deleting
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id, active=True)
        payment.active = False  # Soft delete
        payment.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Pago desactivado exitosamente.'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error al desactivar el pago: {str(e)}'
        }, status=400)


# API Endpoints for AJAX functionality (Student)

def search_students(request):
    """
    AJAX endpoint to search students
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    students = Student.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(school__icontains=query),
        active=True
    ).select_related('group')[:10]  # Limit to 10 results
    
    results = []
    for student in students:
        results.append({
            'id': student.id,
            'full_name': student.full_name,
            'school': student.school or '',
            'group': student.group.group_name if student.group else '',
            'age': student.age
        })
    
    return JsonResponse({'results': results})

def search_parents(request):
    """
    AJAX endpoint to search parents
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    parents = Parent.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    )[:10]  # Limit to 10 results
    
    results = []
    for parent in parents:
        results.append({
            'id': parent.id,
            'full_name': parent.full_name,
            'email': parent.email,
            'phone': parent.phone or ''
        })
    
    return JsonResponse({'results': results})

@require_http_methods(["POST"])
def validate_student_parent(request):
    """
    AJAX endpoint to validate student-parent relationship
    """
    try:
        data = json.loads(request.body)
        student_id = data.get('student_id')
        parent_id = data.get('parent_id')
        
        if not student_id or not parent_id:
            return JsonResponse({'valid': False, 'message': 'Missing student or parent ID'})
        
        # Check if relationship exists
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)
        
        is_valid = student.parents.filter(id=parent_id).exists()
        
        response_data = {
            'valid': is_valid,
            'message': 'Valid relationship' if is_valid else 'Invalid relationship'
        }
        
        # If valid, include enrollment info
        if is_valid:
            active_enrollment = student.enrollments.filter(status='active').first()
            if active_enrollment:
                response_data['enrollment'] = {
                    'id': active_enrollment.id,
                    'enrollment_type': active_enrollment.enrollment_type.display_name,
                    'remaining_amount': str(active_enrollment.remaining_amount),
                    'schedule_type': active_enrollment.get_schedule_type_display(),
                    'is_paid': active_enrollment.is_paid
                }
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'Invalid JSON data'}, status=400)
    except Exception as e:
        return JsonResponse({'valid': False, 'message': str(e)}, status=400)


# API Endpoints for AJAX functionality (Payment)

def search_payments(request):
    """
    AJAX endpoint to search payments
    """
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    payments = Payment.objects.filter(
        Q(student__first_name__icontains=query) |
        Q(student__last_name__icontains=query) |
        Q(parent__first_name__icontains=query) |
        Q(parent__last_name__icontains=query) |
        Q(concept__icontains=query) |
        Q(reference_number__icontains=query)
    ).select_related('student', 'parent', 'enrollment').order_by('-created_at')[:10]
    
    results = []
    for payment in payments:
        results.append({
            'id': payment.id,
            'student_name': payment.student.full_name,
            'parent_name': payment.parent.full_name,
            'amount': str(payment.amount),
            'currency': payment.currency,
            'payment_type': payment.get_payment_type_display(),
            'payment_status': payment.get_payment_status_display(),
            'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else '',
            'payment_date': payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
            'concept': payment.concept,
            'reference_number': payment.reference_number
        })
    
    return JsonResponse({'results': results})

@require_http_methods(["POST"])
def create_payment(request):
    """
    AJAX endpoint to create new payment
    """
    try:
        # Parse form data (works with both FormData and JSON)
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Get required data
        student_id = data.get('student_id')
        parent_id = data.get('parent_id')
        
        print(f"=== CREATE PAYMENT DEBUG ===")
        print(f"Student ID: {student_id}")
        print(f"Parent ID: {parent_id}")
        print(f"Data: {data}")
        
        # Validate required fields
        if not student_id or not parent_id:
            return JsonResponse({
                'success': False,
                'error': 'Student ID and Parent ID are required'
            }, status=400)
        
        # Validate student and parent exist
        student = get_object_or_404(Student, id=student_id)
        parent = get_object_or_404(Parent, id=parent_id)
        
        # Validate relationship
        if not student.parents.filter(id=parent_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'El padre/tutor seleccionado no está asociado con este estudiante.'
            }, status=400)
        
        # Get enrollment if exists
        enrollment = student.enrollments.filter(status='active').first()
        
        # Get payment_date, handle empty string
        payment_date = data.get('payment_date')
        if payment_date == '':
            payment_date = None
        
        # Create payment
        print("Creating payment...")
        payment = Payment.objects.create(
            student=student,
            parent=parent,
            enrollment=enrollment,
            payment_type=data.get('payment_type'),
            payment_method=data.get('payment_method'),
            amount=Decimal(data.get('amount')),
            currency=data.get('currency', 'EUR'),
            payment_status=data.get('payment_status', 'pending'),
            due_date=data.get('due_date'),
            payment_date=payment_date,
            concept=data.get('concept'),
            reference_number=data.get('reference_number', ''),
            observations=data.get('observations', '')
        )
        
        print(f"Payment created successfully: {payment.id}")
        
        return JsonResponse({
            'success': True,
            'message': f'Pago creado exitosamente para {student.full_name}.',
            'payment': {
                'id': payment.id,
                'student_name': payment.student.full_name,
                'parent_name': payment.parent.full_name,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'payment_status': payment.get_payment_status_display(),
                'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else '',
                'concept': payment.concept
            }
        })
        
    except Decimal.InvalidOperation:
        return JsonResponse({
            'success': False,
            'error': 'Monto inválido. Por favor ingrese un número válido.'
        }, status=400)
    except Exception as e:
        print(f"ERROR creating payment: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Error al crear el pago: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def update_payment(request, payment_id):
    """
    AJAX endpoint to update existing payment
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        # Parse data
        if request.content_type == 'application/json':
            data = json.loads(request.body)
        else:
            data = request.POST
        
        # Update fields
        if 'payment_type' in data:
            payment.payment_type = data['payment_type']
        if 'payment_method' in data:
            payment.payment_method = data['payment_method']
        if 'amount' in data:
            payment.amount = Decimal(data['amount'])
        if 'currency' in data:
            payment.currency = data['currency']
        if 'payment_status' in data:
            payment.payment_status = data['payment_status']
        if 'due_date' in data:
            payment.due_date = data['due_date']
        if 'payment_date' in data:
            payment.payment_date = data['payment_date'] if data['payment_date'] else None
        if 'concept' in data:
            payment.concept = data['concept']
        if 'reference_number' in data:
            payment.reference_number = data['reference_number']
        if 'observations' in data:
            payment.observations = data['observations']
        
        payment.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Pago actualizado exitosamente.',
            'payment': {
                'id': payment.id,
                'payment_status': payment.get_payment_status_display(),
                'amount': str(payment.amount)
            }
        })
        
    except Exception as e:
        print(f"ERROR updating payment: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Error al actualizar el pago: {str(e)}'
        }, status=500)

@require_http_methods(["POST"])
def delete_payment(request, payment_id):
    """
    AJAX endpoint to delete payment
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        student_name = payment.student.full_name
        
        payment.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Pago de {student_name} eliminado exitosamente.'
        })
        
    except Exception as e:
        print(f"ERROR deleting payment: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return JsonResponse({
            'success': False,
            'error': f'Error al eliminar el pago: {str(e)}'
        }, status=500)

@require_http_methods(["GET"])
def get_payment_details(request, payment_id):
    """
    AJAX endpoint to get payment details
    """
    try:
        payment = get_object_or_404(Payment, id=payment_id)
        
        return JsonResponse({
            'success': True,
            'payment': {
                'id': payment.id,
                'student_id': payment.student.id,
                'student_name': payment.student.full_name,
                'parent_id': payment.parent.id,
                'parent_name': payment.parent.full_name,
                'enrollment_id': payment.enrollment.id if payment.enrollment else None,
                'payment_type': payment.payment_type,
                'payment_method': payment.payment_method,
                'amount': str(payment.amount),
                'currency': payment.currency,
                'payment_status': payment.payment_status,
                'due_date': payment.due_date.strftime('%Y-%m-%d') if payment.due_date else '',
                'payment_date': payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
                'concept': payment.concept,
                'reference_number': payment.reference_number,
                'observations': payment.observations,
                'created_at': payment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al obtener los detalles del pago: {str(e)}'
        }, status=500)


# Additional utility views

def payment_statistics(request):
    """
    Get payment statistics for dashboard
    """
    today = date.today()
    
    stats = {
        'total_payments': Payment.objects.filter(active=True).count(),
        'completed_payments': Payment.objects.filter(
            active=True, payment_status='completed'
        ).count(),
        'pending_payments': Payment.objects.filter(
            active=True, payment_status='pending'
        ).count(),
        'overdue_payments': Payment.objects.filter(
            active=True, payment_status='pending', due_date__lt=today
        ).count(),
        'total_amount_pending': Payment.objects.filter(
            active=True, payment_status='pending'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00'),
        'total_amount_completed': Payment.objects.filter(
            active=True, payment_status='completed'
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0.00')
    }
    
    return JsonResponse(stats)

def export_payments(request):
    """
    Export payments to CSV
    """
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="pagos.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Estudiante', 'Padre/Tutor', 'Concepto', 'Cantidad', 
        'Método', 'Estado', 'Fecha Vencimiento', 'Fecha Pago', 'Creado'
    ])
    
    payments = Payment.objects.filter(active=True).select_related(
        'student', 'parent'
    ).order_by('-created_at')
    
    for payment in payments:
        writer.writerow([
            payment.id,
            payment.student.full_name,
            payment.parent.full_name,
            payment.concept,
            payment.amount,
            payment.get_payment_method_display(),
            payment.get_payment_status_display(),
            payment.due_date.strftime('%d/%m/%Y') if payment.due_date else '',
            payment.payment_date.strftime('%d/%m/%Y') if payment.payment_date else '',
            payment.created_at.strftime('%d/%m/%Y %H:%M')
        ])
    
    return response

