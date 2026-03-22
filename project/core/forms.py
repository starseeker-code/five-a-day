from django.forms import ModelForm, inlineformset_factory
from core.models import Payment, Student, Parent, Enrollment, EnrollmentType, Group, Teacher, SiteConfiguration

from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from datetime import date
from .models import Student, Parent, Enrollment, EnrollmentType, Group, SiteConfiguration, academic_year_start_date, academic_year_end_date, current_academic_year
from . import constants

# Clases de Tailwind para inputs consistentes
TAILWIND_INPUT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_SELECT_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_TEXTAREA_CLASSES = 'w-full px-3 py-2 border border-neutral-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500'
TAILWIND_CHECKBOX_CLASSES = 'form-checkbox h-5 w-5 text-primary-600'


DATE_INPUT_FORMATS = ["%Y-%m-%d", "%d/%m/%Y"]


# Unified enrollment plan choices (replaces enrollment_type + schedule_type + payment_modality)
ENROLLMENT_PLAN_CHOICES = [
    ('monthly_full', 'Mensual (2 días/semana)'),
    ('monthly_part', 'Mensual (1 día/semana)'),
    ('quarterly', 'Trimestral'),
]

DISCOUNT_CHOICES = [
    ('0', 'Sin descuento'),
    ('5', '5% — Hermano / Trimestral'),
    ('10', '10%'),
    ('15', '15%'),
    ('20', '20%'),
    ('25', '25% — Solo 3 semanas'),
    ('50', '50% — Medio mes (septiembre)'),
    ('75', '75% — Solo 1 semana'),
]


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

    def clean_dni(self):
        dni = self.cleaned_data.get('dni', '').upper().strip()
        if dni and len(dni) < 8:
            raise forms.ValidationError('El DNI debe tener al menos 8 caracteres')
        return dni


class EnrollmentForm(forms.Form):
    """
    Simplified enrollment form. For children: choose a plan (monthly 2d, 1d, quarterly).
    For adults: plan is fixed (handled in view). Discount is a dropdown.
    """
    enrollment_plan = forms.ChoiceField(
        choices=ENROLLMENT_PLAN_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_enrollment_plan'}),
        label='Tipo de matrícula',
    )
    discount = forms.ChoiceField(
        choices=DISCOUNT_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_discount'}),
        label='Descuento',
    )
    has_language_cheque = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Cheque idioma',
    )
    is_sibling_discount = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        label='Descuento hermano',
    )
    # For special/adult manual price
    is_special = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_special'}),
        label='Precio especial',
    )
    manual_amount = forms.DecimalField(
        required=False,
        min_value=Decimal('0.01'),
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Precio personalizado',
            'id': 'id_manual_amount',
        }),
        label='Precio manual (€)',
    )

    def clean(self):
        cleaned_data = super().clean()
        is_special = cleaned_data.get('is_special')
        manual_amount = cleaned_data.get('manual_amount')
        if is_special and not manual_amount:
            raise forms.ValidationError('Debes especificar un precio manual para matrícula especial')
        return cleaned_data

    def create_enrollment(self, student, is_adult=False):
        """Create and save an Enrollment from form data."""
        config = SiteConfiguration.get_config()
        academic_year = current_academic_year()
        start_year = int(academic_year.split('-')[0])
        end_year = int(academic_year.split('-')[1])
        today = date.today()

        is_special = self.cleaned_data.get('is_special', False)
        manual_amount = self.cleaned_data.get('manual_amount')
        discount_pct = Decimal(self.cleaned_data.get('discount', '0'))

        if is_adult:
            if is_special and manual_amount:
                enrollment_type = EnrollmentType.objects.get(name='special')
                base_amount = manual_amount
                schedule_type = 'adult_group'
                payment_modality = 'monthly'
            else:
                enrollment_type = EnrollmentType.objects.get(name='adults')
                base_amount = config.adult_group_monthly_fee
                schedule_type = 'adult_group'
                payment_modality = 'monthly'
        else:
            plan = self.cleaned_data.get('enrollment_plan', 'monthly_full')
            if plan == 'monthly_full':
                enrollment_type = EnrollmentType.objects.get(name='monthly')
                base_amount = config.full_time_monthly_fee
                schedule_type = 'full_time'
                payment_modality = 'monthly'
            elif plan == 'monthly_part':
                enrollment_type = EnrollmentType.objects.get(name='monthly')
                base_amount = config.part_time_monthly_fee
                schedule_type = 'part_time'
                payment_modality = 'monthly'
            elif plan == 'quarterly':
                enrollment_type = EnrollmentType.objects.get(name='quarterly')
                base_amount = config.full_time_monthly_fee
                schedule_type = 'full_time'
                payment_modality = 'quarterly'
            else:
                enrollment_type = EnrollmentType.objects.get(name='monthly')
                base_amount = config.full_time_monthly_fee
                schedule_type = 'full_time'
                payment_modality = 'monthly'

            # Override with special if checked
            if is_special and manual_amount:
                enrollment_type = EnrollmentType.objects.get(name='special')
                base_amount = manual_amount

        discount_amount = base_amount * (discount_pct / Decimal('100'))
        final_amount = base_amount - discount_amount

        enrollment = Enrollment(
            student=student,
            enrollment_type=enrollment_type,
            enrollment_period_start=academic_year_start_date(start_year),
            enrollment_period_end=academic_year_end_date(end_year),
            academic_year=academic_year,
            schedule_type=schedule_type,
            payment_modality=payment_modality,
            has_language_cheque=self.cleaned_data.get('has_language_cheque', False),
            is_sibling_discount=self.cleaned_data.get('is_sibling_discount', False),
            enrollment_amount=base_amount,
            discount_percentage=discount_pct,
            final_amount=final_amount,
            status='active',
            enrollment_date=today,
        )
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
