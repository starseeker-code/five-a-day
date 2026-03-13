from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum
from . import constants


def current_academic_year(reference_date=None):
    """Return academic year in YYYY-YYYY format (starts in September)."""
    reference_date = reference_date or date.today()
    if reference_date.month >= 9:
        start_year = reference_date.year
    else:
        start_year = reference_date.year - 1
    return f"{start_year}-{start_year + 1}"


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
        try:
            config = cls.objects.get(pk=1)
        except cls.DoesNotExist:
            config = cls.objects.create(
                pk=1,
                children_enrollment_fee=constants.CHILDREN_ENROLLMENT_FEE,
                adult_enrollment_fee=constants.ADULT_ENROLLMENT_FEE,
                full_time_monthly_fee=constants.FULL_TIME_MONTHLY_FEE,
                part_time_monthly_fee=constants.PART_TIME_MONTHLY_FEE,
                adult_group_monthly_fee=constants.ADULT_GROUP_MONTHLY_FEE,
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
        'Student',
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
            
            discount_amount = base_amount * (self.discount_percentage / 100)
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
        'Student',
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
        'Parent',
        on_delete=models.PROTECT,
        related_name='payments'
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
        
        # Validate student-parent relationship
        if self.student and self.parent:
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

class Teacher(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True)
    active = models.BooleanField(default=True)
    admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teachers'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['active']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Group(models.Model):
    group_name = models.CharField(max_length=100, unique=True)
    color = models.CharField(max_length=7, default='#6366f1')
    teacher = models.ForeignKey(
        Teacher,
        on_delete=models.PROTECT,
        related_name='groups'
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'groups'
        indexes = [
            models.Index(fields=['group_name']),
            models.Index(fields=['teacher']),
        ]

    def __str__(self):
        return self.group_name


class ScheduleSlot(models.Model):
    """Persists which group is assigned to each schedule slot (row, day, col)."""
    row = models.IntegerField()   # 0, 1, 2
    day = models.IntegerField()   # 0=Mon … 4=Fri
    col = models.IntegerField()   # 0 or 1
    group = models.ForeignKey(
        Group, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='schedule_slots'
    )

    class Meta:
        unique_together = [('row', 'day', 'col')]
        ordering = ['row', 'day', 'col']

    def __str__(self):
        return f"Slot row={self.row} day={self.day} col={self.col}"


class Parent(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    dni = models.CharField(max_length=20, unique=True)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    iban = models.CharField(max_length=34, blank=True)  # International Bank Account Number
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # Added for consistency

    class Meta:
        db_table = 'parents'
        indexes = [
            models.Index(fields=['dni']),
            models.Index(fields=['email']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.dni})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Student(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    school = models.CharField(max_length=200, blank=True)
    allergies = models.TextField(blank=True)
    gdpr_signed = models.BooleanField(default=False)
    group = models.ForeignKey(
        Group,
        on_delete=models.PROTECT,
        related_name='students'
    )
    parents = models.ManyToManyField(
        Parent,
        through='StudentParent',
        related_name='children'
    )
    active = models.BooleanField(default=True)
    withdrawal_date = models.DateField(null=True, blank=True)
    withdrawal_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        indexes = [
            models.Index(fields=['group']),
            models.Index(fields=['active']),
            models.Index(fields=['birth_date']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

class StudentParent(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    parent = models.ForeignKey(Parent, on_delete=models.CASCADE)

    class Meta:
        db_table = 'student_parents'
        unique_together = ('student', 'parent')  # Prevent duplicate relationships

    def __str__(self):
        return f"{self.parent} -> {self.student}"


class TodoItem(models.Model):
    text = models.CharField(max_length=500)
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'todo_items'
        ordering = ['due_date', 'created_at']

    def __str__(self):
        return f"{self.text} ({self.due_date})"

    @property
    def is_overdue(self):
        return self.due_date < date.today()
