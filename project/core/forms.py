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


# Unified enrollment plan choices
ENROLLMENT_PLAN_CHOICES = [
    ('monthly_full', 'Mensual (2 días/semana)'),
    ('monthly_part', 'Mensual (1 día/semana)'),
    ('quarterly', 'Trimestral'),
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
    Simplified enrollment form.
    Children: choose plan (monthly 2d, 1d, quarterly) + checkboxes for discounts.
    Adults: plan is fixed (handled in view). Special checkbox enables manual price.
    """
    enrollment_plan = forms.ChoiceField(
        choices=ENROLLMENT_PLAN_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_enrollment_plan'}),
        label='Tipo de matrícula',
    )
    has_language_cheque = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_has_language_cheque'}),
        label='Cheque idioma',
    )
    is_sibling_discount = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_sibling_discount'}),
        label='Descuento hermano',
    )
    sibling_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'id_sibling_id'}),
    )
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
        has_lc = self.cleaned_data.get('has_language_cheque', False)
        has_sibling = self.cleaned_data.get('is_sibling_discount', False)

        if is_adult:
            if is_special and manual_amount:
                enrollment_type = EnrollmentType.objects.get(name='special')
                base_amount = manual_amount
            else:
                enrollment_type = EnrollmentType.objects.get(name='adults')
                base_amount = config.adult_group_monthly_fee
            schedule_type = 'adult_group'
            payment_modality = 'monthly'
        else:
            plan = self.cleaned_data.get('enrollment_plan', 'monthly_full')

            if is_special and manual_amount:
                enrollment_type = EnrollmentType.objects.get(name='special')
                base_amount = manual_amount
                if plan == 'monthly_full':
                    schedule_type = 'full_time'
                    payment_modality = 'monthly'
                elif plan == 'monthly_part':
                    schedule_type = 'part_time'
                    payment_modality = 'monthly'
                else:
                    schedule_type = 'full_time'
                    payment_modality = 'quarterly'
            elif plan == 'monthly_full':
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
                # Quarterly = 3 months * full_time price - 5%
                quarterly_base = config.full_time_monthly_fee * 3
                quarterly_discount = config.quarterly_enrollment_discount  # 5%
                base_amount = quarterly_base * (1 - quarterly_discount / 100)
                schedule_type = 'full_time'
                payment_modality = 'quarterly'
            else:
                enrollment_type = EnrollmentType.objects.get(name='monthly')
                base_amount = config.full_time_monthly_fee
                schedule_type = 'full_time'
                payment_modality = 'monthly'

        # Apply discounts
        discount_pct = Decimal('0')
        final_amount = base_amount

        if has_sibling and not is_adult:
            discount_pct += config.sibling_discount  # 5%
            final_amount = base_amount * (1 - config.sibling_discount / 100)

        if has_lc and not is_adult:
            # Language cheque is flat discount per month
            lc_amount = config.language_cheque_discount
            if payment_modality == 'quarterly':
                lc_amount = lc_amount * 3
            final_amount = final_amount - lc_amount

        # Ensure minimum
        if final_amount < Decimal('0.01'):
            final_amount = Decimal('0.01')

        enrollment = Enrollment(
            student=student,
            enrollment_type=enrollment_type,
            enrollment_period_start=academic_year_start_date(start_year),
            enrollment_period_end=academic_year_end_date(end_year),
            academic_year=academic_year,
            schedule_type=schedule_type,
            payment_modality=payment_modality,
            has_language_cheque=has_lc,
            is_sibling_discount=has_sibling,
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
    extra=1,
    can_delete=True,
    widgets={
        'parent': forms.Select(attrs={'class': 'form-control'})
    }
)
