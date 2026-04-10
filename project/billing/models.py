from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from datetime import date, timedelta
from django.core.exceptions import ValidationError
from billing import constants


def current_academic_year(reference_date=None):
    """Return academic year in YYYY-YYYY format (starts in September)."""
    reference_date = reference_date or date.today()
    if reference_date.month >= 9:
        start_year = reference_date.year
    else:
        start_year = reference_date.year - 1
    return f"{start_year}-{start_year + 1}"


def academic_year_start_date(year):
    """
    Return the first Monday on or after September 14th of the given year.
    This is the start of the academic year (3rd week of September).
    """
    sept_14 = date(year, 9, 14)
    # Monday = 0, so we need to find the next Monday on or after Sept 14
    days_until_monday = (7 - sept_14.weekday()) % 7
    return sept_14 + timedelta(days=days_until_monday)


def academic_year_end_date(year):
    """
    Return the last Friday of June of the given year.
    """
    # Start from June 30 and go backwards to find Friday (weekday=4)
    june_30 = date(year, 6, 30)
    days_since_friday = (june_30.weekday() - 4) % 7
    return june_30 - timedelta(days=days_since_friday)


# ============================================================================
# SITE CONFIGURATION - Singleton para configuración del sitio
# ============================================================================

class SiteConfiguration(models.Model):
    """
    Modelo singleton para almacenar configuración editable del sitio.
    Solo debe existir una instancia de este modelo.
    """

    # Matrícula (Enrollment Fees)
    children_enrollment_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('40.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Matrícula niños'
    )
    adult_enrollment_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Matrícula adultos'
    )

    # Mensualidades (Monthly Fees)
    full_time_monthly_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('54.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Mensualidad jornada completa'
    )
    part_time_monthly_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('36.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Mensualidad media jornada'
    )
    adult_group_monthly_fee = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('60.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Mensualidad grupo adultos'
    )

    # Descuentos (Discounts)
    language_cheque_discount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Cheque idioma (€ fijo)'
    )
    quarterly_enrollment_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Matrícula trimestral (%)'
    )
    old_student_discount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Alumno antiguo (€ fijo)'
    )
    june_discount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Descuento junio — completar año (€ fijo)'
    )
    full_year_bonus = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('20.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Año completo (€ fijo, no adultos)'
    )
    sibling_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('5.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Hermanos (% mensual)'
    )
    half_month_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Medio mes — septiembre (%)'
    )
    one_week_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('75.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Solo 1 semana — primer mes (%)'
    )
    three_week_discount = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('25.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name='Solo 3 semanas (%)'
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'site_configuration'
        verbose_name = 'Configuración del sitio'
        verbose_name_plural = 'Configuración del sitio'

    def __str__(self):
        return 'Configuración del sitio'

    def save(self, *args, **kwargs):
        """Ensure only one instance exists (singleton pattern)"""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion of the singleton"""
        pass

    @classmethod
    def get_config(cls):
        """
        Obtiene la configuración del sitio (crea una si no existe).
        Usa valores por defecto de constants.py si no hay configuración.
        """
        config, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'children_enrollment_fee': constants.CHILDREN_ENROLLMENT_FEE,
                'adult_enrollment_fee': constants.ADULT_ENROLLMENT_FEE,
                'full_time_monthly_fee': constants.FULL_TIME_MONTHLY_FEE,
                'part_time_monthly_fee': constants.PART_TIME_MONTHLY_FEE,
                'adult_group_monthly_fee': constants.ADULT_GROUP_MONTHLY_FEE,
                'language_cheque_discount': constants.LANGUAGE_CHEQUE_DISCOUNT[0],
                'quarterly_enrollment_discount': constants.QUARTERLY_ENROLLMENT_DISCOUNT[0],
                'old_student_discount': constants.OLD_STUDENT_DISCOUNT[0],
                'june_discount': constants.JUNE_DISCOUNT[0],
                'full_year_bonus': constants.FULL_YEAR_BONUS[0],
                'sibling_discount': constants.SIBLING_DISCOUNT[0],
                'half_month_discount': constants.HALF_MONTH_DISCOUNT[0],
                'one_week_discount': constants.ONE_WEEK_DISCOUNT[0],
                'three_week_discount': constants.THREE_WEEK_DISCOUNT[0],
            }
        )
        return config


class EnrollmentType(models.Model):
    name = models.CharField(
        max_length=20,
        choices=constants.ENROLLMENT_TYPE_CHOICES,
        unique=True
    )
    display_name = models.CharField(max_length=50)
    base_amount_full_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    base_amount_part_time = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollment_types'

    def __str__(self):
        return self.display_name

class Enrollment(models.Model):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='enrollments'
    )
    enrollment_type = models.ForeignKey(
        EnrollmentType,
        on_delete=models.PROTECT,
        related_name='enrollments'
    )

    enrollment_period_start = models.DateField()
    enrollment_period_end = models.DateField()
    academic_year = models.CharField(max_length=9, default=current_academic_year)
    schedule_type = models.CharField(
        max_length=20,
        choices=constants.SCHEDULE_TYPE_CHOICES,
        default='full_time'
    )
    payment_modality = models.CharField(
        max_length=10,
        choices=constants.PAYMENT_MODALITY_CHOICES,
        default='monthly',
        verbose_name='Modalidad de pago'
    )
    has_language_cheque = models.BooleanField(
        default=False,
        verbose_name='Cheque idioma'
    )
    is_sibling_discount = models.BooleanField(
        default=False,
        verbose_name='Descuento hermano'
    )

    enrollment_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(constants.MIN_ENROLLMENT_AMOUNT)]
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))]
    )
    final_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(constants.MIN_ENROLLMENT_AMOUNT)]
    )

    status = models.CharField(
        max_length=10,
        choices=constants.ENROLLMENT_STATUS_CHOICES,
        default='pending'
    )
    enrollment_date = models.DateField()

    document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollments'
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['status']),
            models.Index(fields=['enrollment_date']),
            models.Index(fields=['enrollment_period_start']),
        ]
        # Prevent overlapping active enrollments for the same student
        constraints = [
            models.UniqueConstraint(
                fields=['student'],
                condition=models.Q(status='active'),
                name='unique_active_enrollment_per_student'
            )
        ]

    def __str__(self):
        return f"{self.student} - {self.enrollment_type} ({self.get_schedule_type_display()})"

    def save(self, *args, **kwargs):
        """
        Auto-calculate final_amount based on enrollment_type and schedule_type
        """
        if not self.final_amount:
            base_amount = (
                self.enrollment_type.base_amount_full_time
                if self.schedule_type == 'full_time'
                else self.enrollment_type.base_amount_part_time
            )

            discount_amount = base_amount * (self.discount_percentage / Decimal('100'))
            self.final_amount = base_amount - discount_amount

            if not self.enrollment_amount:
                self.enrollment_amount = self.final_amount

        super().save(*args, **kwargs)

    @property
    def is_paid(self):
        """Check if enrollment is fully paid"""
        total_payments = self.payments.filter(
            payment_status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return total_payments >= self.final_amount

    @property
    def remaining_amount(self):
        """Calculate remaining amount to be paid"""
        total_payments = self.payments.filter(
            payment_status='completed'
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')

        return max(self.final_amount - total_payments, Decimal('0.00'))

class Payment(models.Model):
    student = models.ForeignKey(
        'students.Student',
        on_delete=models.PROTECT,
        related_name='payments'
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )
    parent = models.ForeignKey(
        'students.Parent',
        on_delete=models.PROTECT,
        related_name='payments',
        null=True,
        blank=True
    )

    payment_type = models.CharField(
        max_length=20,
        choices=constants.PAYMENT_TYPE_CHOICES,
        default='monthly'
    )
    payment_method = models.CharField(
        max_length=15,
        choices=constants.PAYMENT_METHOD_CHOICES,
        default='transfer'
    )

    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(constants.MIN_PAYMENT_AMOUNT)]
    )
    currency = models.CharField(max_length=3, default=constants.DEFAULT_CURRENCY)

    payment_status = models.CharField(
        max_length=10,
        choices=constants.PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    due_date = models.DateField()  # When payment is expected
    payment_date = models.DateField(null=True, blank=True)  # When payment was actually made

    concept = models.CharField(max_length=200)
    reference_number = models.CharField(max_length=50, blank=True)  # Bank reference, receipt number, etc.

    observations = models.TextField(blank=True)
    document_url = models.URLField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payments'
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['parent']),
            models.Index(fields=['payment_status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['enrollment']),
        ]

    def __str__(self):
        return f"{self.student} - {self.concept} - €{self.amount} ({self.get_payment_status_display()})"

    def clean(self):
        """Validation logic"""

        # If payment is completed, payment_date should be set
        if self.payment_status == 'completed' and not self.payment_date:
            self.payment_date = date.today()

        # Payment date should not be in the future for completed payments
        if self.payment_status == 'completed' and self.payment_date and self.payment_date > date.today():
            raise ValidationError("Payment date cannot be in the future for completed payments.")

        # Validate student-parent relationship (skip for adult students)
        if self.student and self.parent and not self.student.is_adult:
            if not self.student.parents.filter(id=self.parent.id).exists():
                raise ValidationError("The selected parent is not associated with this student.")

    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        return (
            self.payment_status == 'pending' and
            self.due_date is not None and
            self.due_date < date.today()
        )

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0
