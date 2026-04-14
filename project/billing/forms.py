from decimal import Decimal

from django import forms

# Unified enrollment plan choices
ENROLLMENT_PLAN_CHOICES = [
    ("monthly_full", "Mensual (2 días/semana)"),
    ("monthly_part", "Mensual (1 día/semana)"),
    ("quarterly", "Trimestral"),
]


class EnrollmentForm(forms.Form):
    """
    Simplified enrollment form.
    Children: choose plan (monthly 2d, 1d, quarterly) + checkboxes for discounts.
    Adults: plan is fixed (handled in view). Special checkbox enables manual price.
    """

    enrollment_plan = forms.ChoiceField(
        choices=ENROLLMENT_PLAN_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control", "id": "id_enrollment_plan"}),
        label="Tipo de matrícula",
    )
    has_language_cheque = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_has_language_cheque"}),
        label="Cheque idioma",
    )
    is_sibling_discount = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_is_sibling_discount"}),
        label="Descuento hermano",
    )
    sibling_id = forms.IntegerField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_sibling_id"}),
    )
    is_special = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "id": "id_is_special"}),
        label="Precio especial",
    )
    manual_amount = forms.DecimalField(
        required=False,
        min_value=Decimal("0.01"),
        decimal_places=2,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0.01",
                "placeholder": "Precio personalizado",
                "id": "id_manual_amount",
            }
        ),
        label="Precio manual (€)",
    )

    def clean(self):
        cleaned_data = super().clean()
        is_special = cleaned_data.get("is_special")
        manual_amount = cleaned_data.get("manual_amount")
        if is_special and not manual_amount:
            raise forms.ValidationError("Debes especificar un precio manual para matrícula especial")
        return cleaned_data

    def create_enrollment(self, student, is_adult=False):
        """Create and save an Enrollment from form data.
        Delegates to EnrollmentService for business logic."""
        from billing.services.enrollment_service import EnrollmentService

        enrollment_data = {
            "enrollment_plan": self.cleaned_data.get("enrollment_plan", "monthly_full"),
            "has_language_cheque": self.cleaned_data.get("has_language_cheque", False),
            "is_sibling_discount": self.cleaned_data.get("is_sibling_discount", False),
            "is_special": self.cleaned_data.get("is_special", False),
            "manual_amount": self.cleaned_data.get("manual_amount"),
        }
        return EnrollmentService.create_enrollment(student, enrollment_data, is_adult=is_adult)
