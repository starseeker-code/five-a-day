from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum

class EnrollmentType(models.Model):
    # !ELIMINATE
    """
    Defines different enrollment types with their base pricing
    This makes pricing more maintainable and auditable
    """
    ENROLLMENT_TYPES = [
        ('adults', 'Adults'),
        ('special', 'Special'),
        ('languages_ticket', 'Languages Ticket'),
        ('monthly', 'Monthly'),
        ('half_month', 'Half-month'),
        ('quarterly', 'Quarterly'),
    ]
    
    name = models.CharField(
        max_length=20, 
        choices=ENROLLMENT_TYPES,
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
    """
    Improved enrollment model with better structure and logic
    """
    ENROLLMENT_COST = [
        ('children_enrollment', 40),  # enrollment (1 year)
        ('adult_enrollment', 20),  # enrollment (1 year)
    ]
    
    SCHEDULE_TYPES = [
        ('full_time', 'Full-time (2 classes/week)'),  # 54€ / month
        ('part_time', 'Part-time (1 class/week)'),  # 36€ / month
        ('adult_group', 'Part-time (1 class/week)')  # 60€ / month
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('finished', 'Finished'),
        ('cancelled', 'Cancelled'),
        ('suspended', 'Suspended'),
    ]

    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,  # Keep - enrollments are too important to cascade delete
        related_name='enrollments'
    )
    enrollment_type = models.ForeignKey(
        EnrollmentType,
        on_delete=models.PROTECT,  # Don't allow deletion of enrollment types with active enrollments
        related_name='enrollments'
    )
    
    enrollment_period_start = models.DateField()
    enrollment_period_end = models.DateField()
    schedule_type = models.CharField(
        max_length=20,
        choices=SCHEDULE_TYPES,
        default='full_time'
    )
    
    enrollment_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
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
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
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
    """
    Improved payment model with better structure and validation
    """
    # !IMPORTANT payments could be partial (divorced parents)
    PAYMENT_METHODS = [
        ('cash', 'In Cash'),
        ('transfer', 'Transference'),
        ('credit_card', 'Credit Card'),
    ]

    DISCOUNTS = [
        {"language_cheque": (20, "flat")},
        {"quartely_enrollment": (0.05, "percentage")},  # x3 months
        {"old_student_enrollment": (10, "flat")},
        {"full_year_bonus": (20, "flat")},  # NO adultos, en abril trimestrales tambien se aplica
        {"sibling_discount": (0.05, "percentage")},  # each month
        # ---- let's see first
        {"half-month_discount": (0.5, "percentage")},  # sept
        {"only_one_week_discount": (0.75, "percentage")},  # we should automate this with a calendar system (first month)
        {"only_three_week_discount": (0.25, "percentage")},
    ]

    PAYMENT_STATUS = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]

    PAYMENT_TYPES = [
        ('enrollment', 'Enrollment Fee'),
        ('monthly', 'Monthly Fee'),
        ('materials', 'Materials'),
        ('registration', 'Registration'),
        ('exam', 'Exam Fee'),
        ('other', 'Other'),
    ]

    # Core relationships
    student = models.ForeignKey(
        'Student',
        on_delete=models.PROTECT,  # Payments are critical financial records
        related_name='payments'
    )
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.PROTECT,  # Keep payment history even if enrollment changes
        related_name='payments',
        null=True,
        blank=True  # Some payments might not be tied to specific enrollment
    )
    parent = models.ForeignKey(
        'Parent',
        on_delete=models.PROTECT,  # Keep payment history
        related_name='payments'
    )

    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='monthly'
    )
    payment_method = models.CharField(
        max_length=15,
        choices=PAYMENT_METHODS,
        default='transfer'
    )
    
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='EUR')
    
    payment_status = models.CharField(
        max_length=10,
        choices=PAYMENT_STATUS,
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
        
    # Manager
    #active_objects = ActivePaymentManager()

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
    teacher = models.ForeignKey(
        Teacher, 
        on_delete=models.PROTECT,  # Prevent deletion if group exists
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

class Parent(models.Model):
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    dni = models.CharField(max_length=20, unique=True)  # Spanish ID number
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
    # !IMPORTANT ADULTS DO NOT NEED FK WITH PARENTS (new table for adult_students?)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    email = models.EmailField(blank=True)  # TODO remove
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
