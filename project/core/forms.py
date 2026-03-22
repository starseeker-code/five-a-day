from django.forms import ModelForm, inlineformset_factory
from core.models import Payment, Student, Parent, Enrollment, EnrollmentType, Group, Teacher, SiteConfiguration

from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from datetime import date
from .models import Student, Parent, Enrollment, EnrollmentType, Group, SiteConfiguration, academic_year_start_date, academic_year_end_date
from . import constants

# Clases de Tailwind para inputs consistentes
TAILWIND_INPUT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_SELECT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_TEXTAREA_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_CHECKBOX_CLASSES = 'form-checkbox h-5 w-5 text-primary-600'


DATE_INPUT_FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]


class StudentForm(ModelForm):
    class Meta:
        model = Student
        fields = [
            'first_name', 'last_name', 'birth_date', 'school', 'allergies', 
            'gdpr_signed', 'group']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellidos'}),
            'birth_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['birth_date'].input_formats = DATE_INPUT_FORMATS

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
    academic_year = forms.ChoiceField(
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_academic_year'}),
        label='Curso académico',
        help_text='Ejemplo: 2025-2026'
    )
    
    class Meta:
        model = Enrollment
        fields = [
            'enrollment_type', 'academic_year', 'schedule_type',
            'payment_modality', 'has_language_cheque', 'is_sibling_discount',
            'discount_percentage', 'enrollment_date',
            'notes'
        ]
        widgets = {
            'enrollment_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_enrollment_type'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_schedule_type'}),
            'payment_modality': forms.Select(attrs={'class': 'form-control'}),
            'has_language_cheque': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_sibling_discount': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'discount_percentage': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100', 'step': '0.01'}),
            'enrollment_date': forms.DateInput(format='%Y-%m-%d', attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Notas adicionales'}),
        }
        labels = {
            'enrollment_type': 'Tipo de matrícula',
            'academic_year': 'Curso académico',
            'schedule_type': 'Tipo de horario',
            'payment_modality': 'Modalidad de pago',
            'has_language_cheque': 'Cheque idioma',
            'is_sibling_discount': 'Descuento hermano',
            'discount_percentage': 'Descuento (%)',
            'enrollment_date': 'Fecha de alta de matriculación',
            'notes': 'Notas',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['enrollment_date'].input_formats = DATE_INPUT_FORMATS
        self.fields['academic_year'].initial = self._get_default_academic_year()
        self.fields['academic_year'].choices = [
            (year, year) for year in self._build_academic_year_choices()
        ]

    def _get_default_academic_year(self):
        today = date.today()
        start_year = today.year if today.month >= 9 else today.year - 1
        return f"{start_year}-{start_year + 1}"

    def _build_academic_year_choices(self):
        today = date.today()
        current_start = today.year if today.month >= 9 else today.year - 1
        return [f"{year}-{year + 1}" for year in range(current_start - 2, current_start + 4)]

    def clean_academic_year(self):
        academic_year = (self.cleaned_data.get('academic_year') or '').strip()
        if not academic_year:
            raise forms.ValidationError('El curso académico es obligatorio')

        parts = academic_year.split('-')
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise forms.ValidationError('El formato debe ser YYYY-YYYY (ejemplo: 2025-2026)')

        start_year, end_year = int(parts[0]), int(parts[1])
        if end_year != start_year + 1:
            raise forms.ValidationError('El curso académico debe tener años consecutivos')

        return academic_year

    def clean(self):
        cleaned_data = super().clean()
        enrollment_type = cleaned_data.get('enrollment_type')
        manual_amount = cleaned_data.get('manual_amount')
        
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
        academic_year = self.cleaned_data.get('academic_year')
        
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

        start_year = int(academic_year.split('-')[0])
        end_year = int(academic_year.split('-')[1])

        enrollment.enrollment_amount = base_amount
        enrollment.final_amount = final_amount
        enrollment.academic_year = academic_year
        enrollment.enrollment_period_start = academic_year_start_date(start_year)
        enrollment.enrollment_period_end = academic_year_end_date(end_year)
        enrollment.status = enrollment.status or 'active'
        
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