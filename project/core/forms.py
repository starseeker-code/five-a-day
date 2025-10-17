from django.forms import ModelForm, inlineformset_factory
from core.models import Payment, Student, Parent, Enrollment, EnrollmentType, Group, Teacher

from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal
from .models import Student, Parent, Enrollment, EnrollmentType, Group

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
    class Meta:
        model = Enrollment
        fields = [
            'enrollment_type', 'enrollment_period_start', 
            'enrollment_period_end', 'schedule_type',
            'discount_percentage', 'enrollment_date',
            'status', 'notes'
        ]
        widgets = {
            'enrollment_type': forms.Select(attrs={'class': 'form-control'}),
            'enrollment_period_start': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'enrollment_period_end': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'schedule_type': forms.Select(attrs={'class': 'form-control'}),
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
        
        if start_date and end_date and start_date >= end_date:
            raise forms.ValidationError(
                'La fecha de inicio debe ser anterior a la fecha de fin'
            )
        
        return cleaned_data

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