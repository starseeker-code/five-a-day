from django.forms import ModelForm, inlineformset_factory
from core.models import Payment, Student, Parent, Enrollment, EnrollmentType, Group, Teacher, SiteConfiguration

from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import Student, Parent, Enrollment, EnrollmentType, Group, SiteConfiguration

# Clases de Tailwind para inputs consistentes
TAILWIND_INPUT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_SELECT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_TEXTAREA_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_CHECKBOX_CLASSES = 'form-checkbox h-5 w-5 text-primary-600'


class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'school', 'allergies', 
            'gdpr_signed', 'group']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'birth_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'school': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Colegio'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Alergias'}),
            'gdpr_signed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'group': forms.Select(attrs={'class': 'form-control'})
        }
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'birth_date': 'Fecha de nacimiento',
            'school': 'Colegio',
            'allergies': 'Alergias',
            'gdpr_signed': 'GDPR Firmado',
            'group': 'Grupo',
        }

    def clean_birth_date(self):
        from datetime import date
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date and birth_date > date.today():
            raise forms.ValidationError('La fecha de nacimiento no puede ser futura')
        return birth_date

class ParentForm(forms.ModelForm):
    class Meta:
        model = Parent
        fields = [
            'first_name', 'last_name', 'dni', 
            'phone', 'email', 'iban'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'dni': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678A'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@ejemplo.com'}),
            'iban': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ES00 0000 0000 00 0000000000'}),
        }
        labels = {
            'first_name': 'Nombre del padre/madre',
            'last_name': 'Apellidos',
            'dni': 'DNI/NIE',
            'phone': 'Teléfono',
            'email': 'Email',
            'iban': 'IBAN (opcional)',
        }

    def clean_dni(self):  # TODO: Email y otros
        dni = self.cleaned_data.get('dni', '').upper().strip()
        if dni and len(dni) < 8:
            raise forms.ValidationError('El DNI debe tener al menos 8 caracteres')
        return dni

class EnrollmentForm(forms.ModelForm):
    # Campo opcional para precio manual (solo para matrículas especiales)
    manual_amount = forms.DecimalField(
        required=False,
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Precio manual (solo para especial)'
        }),
        label='Precio manual (€)',
        help_text='Solo rellenar para matrículas de tipo "Especial"'
    )
    
    class Meta:
        model = Enrollment
        fields = [
            'enrollment_type', 'enrollment_period_start', 
            'enrollment_period_end', 'schedule_type',
            'discount_percentage', 'enrollment_date',
            'status', 'notes'
        ]
        widgets = {
            'enrollment_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_enrollment_type'}),
            'enrollment_period_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'enrollment_period_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_schedule_type'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'enrollment_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionales'}),
        }
        labels = {
            'enrollment_type': 'Tipo de matrícula',
            'enrollment_period_start': 'Inicio del período',
            'enrollment_period_end': 'Fin del período',
            'schedule_type': 'Tipo de horario',
            'discount_percentage': 'Descuento (%)',
            'enrollment_date': 'Fecha de matrícula',
            'status': 'Estado',
            'notes': 'Notas',
        }

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('enrollment_period_start')
        end_date = cleaned_data.get('enrollment_period_end')
        enrollment_type = cleaned_data.get('enrollment_type')
        manual_amount = cleaned_data.get('manual_amount')
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(
                'La fecha de inicio debe ser anterior a la fecha de fin'
            )
        
        # Si es tipo "special", el precio manual es obligatorio
        if enrollment_type and enrollment_type.name == 'special':
            if not manual_amount:
                raise forms.ValidationError(
                    'Para matrículas de tipo "Especial" debes especificar el precio manual'
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Guarda la matrícula calculando automáticamente los precios
        según el tipo de matrícula y horario, o usando el precio manual para especiales.
        """
        enrollment = super().save(commit=False)
        
        enrollment_type = self.cleaned_data.get('enrollment_type')
        schedule_type = self.cleaned_data.get('schedule_type')
        manual_amount = self.cleaned_data.get('manual_amount')
        discount = self.cleaned_data.get('discount_percentage') or Decimal('0.00')
        
        # Obtener configuración del sitio
        config = SiteConfiguration.get_config()
        
        if enrollment_type and enrollment_type.name == 'special':
            # Para especiales, usar el precio manual
            base_amount = manual_amount
        else:
            # Para otros tipos, calcular según schedule_type y configuración
            if schedule_type == 'full_time':
                base_amount = config.full_time_monthly_fee
            elif schedule_type == 'part_time':
                base_amount = config.part_time_monthly_fee
            elif schedule_type == 'adult_group':
                base_amount = config.adult_group_monthly_fee
            else:
                base_amount = config.full_time_monthly_fee  # Default
        
        # Calcular precio final con descuento
        discount_amount = base_amount * (discount / Decimal('100'))
        final_amount = base_amount - discount_amount
        
        enrollment.enrollment_amount = base_amount
        enrollment.final_amount = final_amount
        
        if commit:
            enrollment.save()
        
        return enrollment

# Formset - Herencia de forms
ParentFormSet = inlineformset_factory(
    Student,
    Student.parents.through,  # StudentParent
    fields=('parent',),
    extra=1,  # Forms vacios que se muestran
    can_delete=True,
    widgets={
        'parent': forms.Select(attrs={'class': 'form-control'})
    }
)