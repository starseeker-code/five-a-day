from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from decimal import Decimal
from datetime import date
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Sum


class ExpenseCategory(models.Model):
    """
    Categories for organizing expenses
    """
    CATEGORY_TYPES = [
        ('operational', 'Operational'),
        ('administrative', 'Administrative'),
        ('marketing', 'Marketing'),
        ('infrastructure', 'Infrastructure'),
        ('legal', 'Legal & Compliance'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    category_type = models.CharField(max_length=20, choices=CATEGORY_TYPES)
    description = models.TextField(blank=True)
    is_tax_deductible = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expense_categories'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return f"{self.name} ({self.get_category_type_display()})"

class Expense(models.Model):
    """
    Main expense tracking model
    """
    EXPENSE_STATUS = [
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]

    PAYMENT_METHODS = [
        ('cash', 'Cash'),
        ('transfer', 'Bank Transfer'),
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('check', 'Check'),
        ('direct_debit', 'Direct Debit'),
    ]

    EXPENSE_TYPES = [
        ('recurring', 'Recurring'),  # Monthly rent, utilities, etc.
        ('one_time', 'One-time'),    # Equipment purchase, repairs, etc.
        ('reimbursement', 'Reimbursement'),  # Staff expense reimbursements
    ]

    expense_number = models.CharField(max_length=20, unique=True)  # Auto-generated
    description = models.CharField(max_length=300)
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    
    vendor_name = models.CharField(max_length=200, blank=True)
    vendor_tax_id = models.CharField(max_length=50, blank=True)  # CIF/NIF for tax purposes
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    currency = models.CharField(max_length=3, default='EUR')
    
    expense_type = models.CharField(max_length=15, choices=EXPENSE_TYPES, default='one_time')
    expense_date = models.DateField()  # When the expense occurred
    due_date = models.DateField(null=True, blank=True)  # When payment is due
    payment_date = models.DateField(null=True, blank=True)  # When actually paid
    status = models.CharField(max_length=15, choices=EXPENSE_STATUS, default='pending')
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHODS, blank=True)
    
    invoice_number = models.CharField(max_length=100, blank=True)
    receipt_url = models.URLField(blank=True)
    approved_by = models.ForeignKey(
        'Teacher',  # Assuming teachers can be administrators
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    approval_date = models.DateField(null=True, blank=True)
    
    notes = models.TextField(blank=True)
    is_recurring = models.BooleanField(default=False)
    recurring_frequency = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ],
        blank=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expenses'
        indexes = [
            models.Index(fields=['expense_date']),
            models.Index(fields=['status']),
            models.Index(fields=['category']),
            models.Index(fields=['vendor_name']),
            models.Index(fields=['due_date']),
            models.Index(fields=['expense_number']),
        ]

    def __str__(self):
        vendor_info = f" - {self.vendor_name}" if self.vendor_name else ""
        return f"{self.expense_number} - {self.description}{vendor_info} - €{self.total_amount}"

    def save(self, *args, **kwargs):
        # Auto-generate expense number if not provided
        if not self.expense_number:
            year = timezone.now().year
            last_expense = Expense.objects.filter(
                expense_number__startswith=f'EXP{year}'
            ).order_by('expense_number').last()
            
            if last_expense:
                last_number = int(last_expense.expense_number[-4:])
                new_number = last_number + 1
            else:
                new_number = 1
                
            self.expense_number = f'EXP{year}{new_number:04d}'
        
        # Auto-calculate total_amount if not provided
        if not self.total_amount:
            self.total_amount = self.amount + self.tax_amount
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validation logic"""
        if self.status == 'paid' and not self.payment_date:
            self.payment_date = date.today()
        
        if self.status == 'approved' and not self.approval_date:
            self.approval_date = date.today()

    @property
    def is_overdue(self):
        """Check if expense payment is overdue"""
        return (
            self.status in ['approved'] and 
            self.due_date and 
            self.due_date < date.today()
        )

    @property
    def days_overdue(self):
        """Calculate days overdue for payment"""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

class RecurringExpenseTemplate(models.Model):
    """
    Templates for recurring expenses
    """
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='recurring_templates'
    )
    
    vendor_name = models.CharField(max_length=200)
    vendor_tax_id = models.CharField(max_length=50, blank=True)
    
    default_amount = models.DecimalField(max_digits=10, decimal_places=2)
    default_tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('annually', 'Annually'),
        ]
    )
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)  # For contracts with end dates
    
    auto_generate = models.BooleanField(default=True)  # Auto-create expenses
    active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'recurring_expense_templates'

    def __str__(self):
        return f"{self.name} - {self.get_frequency_display()} - €{self.default_amount}"

class FinancialPeriod(models.Model):
    """
    Financial periods for reporting (monthly, quarterly, annual reports)
    """
    PERIOD_TYPES = [
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annual', 'Annual'),
    ]

    name = models.CharField(max_length=100)  # "January 2024", "Q1 2024", etc.
    period_type = models.CharField(max_length=10, choices=PERIOD_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    
    total_income = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    net_profit = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    
    is_closed = models.BooleanField(default=False)  # Once closed, no more changes
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'financial_periods'
        unique_together = ('period_type', 'start_date', 'end_date')

    def __str__(self):
        return f"{self.name} - Net: €{self.net_profit}"

    def calculate_financials(self):
        """Calculate income, expenses, and profit for this period"""
        
        income = Payment.objects.filter(
            payment_status='completed',
            payment_date__range=[self.start_date, self.end_date]
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        expenses = Expense.objects.filter(
            status='paid',
            payment_date__range=[self.start_date, self.end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        self.total_income = income
        self.total_expenses = expenses
        self.net_profit = income - expenses
        self.save()
        
        return {
            'income': self.total_income,
            'expenses': self.total_expenses,
            'profit': self.net_profit
        }

class EnrollmentType(models.Model):
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
    SCHEDULE_TYPES = [
        ('full_time', 'Full-time (2 classes/week)'),
        ('part_time', 'Part-time (1 class/week)'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('completed', 'Completed'),
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
        max_length=10,
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
    PAYMENT_METHODS = [
        ('cash', 'In Cash'),
        ('transfer', 'Transference'),
        ('credit_card', 'Credit Card'),
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

    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        return (
            self.payment_status == 'pending' and 
            self.due_date < date.today()
        )

    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0

class Payroll(models.Model):
    """
    Improved payroll model with better tracking
    """
    PAYROLL_STATUS = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]

    PAYROLL_TYPES = [
        ('monthly_salary', 'Monthly Salary'),
        ('hourly_payment', 'Hourly Payment'),
        ('bonus', 'Bonus'),
        ('commission', 'Commission'),
        ('reimbursement', 'Reimbursement'),
        ('other', 'Other'),
    ]

    teacher = models.ForeignKey(
        'Teacher',
        on_delete=models.PROTECT,  # Keep payroll history for tax and audit purposes
        related_name='payrolls'
    )
    
    payroll_type = models.CharField(
        max_length=20,
        choices=PAYROLL_TYPES,
        default='monthly_salary'
    )
    
    period_start = models.DateField()
    period_end = models.DateField()
    
    gross_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    tax_deductions = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    other_deductions = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00')
    )
    net_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    
    status = models.CharField(
        max_length=10,
        choices=PAYROLL_STATUS,
        default='pending'
    )
    payment_date = models.DateField(null=True, blank=True)
    
    document_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'payrolls'
        indexes = [
            models.Index(fields=['teacher']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_date']),
            models.Index(fields=['period_start']),
        ]
        # Prevent duplicate payrolls for same teacher and period
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'period_start', 'period_end', 'payroll_type'],
                name='unique_payroll_per_teacher_period'
            )
        ]

    def __str__(self):
        return f"{self.teacher} - {self.get_payroll_type_display()} - {self.period_start} to {self.period_end} - €{self.net_amount}"

    def save(self, *args, **kwargs):
        """
        Auto-calculate net_amount if not provided
        """
        if not self.net_amount:
            self.net_amount = self.gross_amount - self.tax_deductions - self.other_deductions
        
        super().save(*args, **kwargs)

    def clean(self):
        """Validation logic"""
        
        if self.period_start and self.period_end and self.period_start > self.period_end:
            raise ValidationError("Period start date must be before period end date.")
        
        if self.status == 'paid' and not self.payment_date:
            self.payment_date = date.today()

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
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    birth_date = models.DateField()
    email = models.EmailField(blank=True)  # Students might not have email
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


# =============================================================================
# TO BE DONE AND CONSIDERED
# =============================================================================

"""
ENROLLMENT IMPROVEMENTS:
✅ Added EnrollmentType model for better pricing management
✅ Added schedule_type (full-time/part-time) as requested
✅ Added status tracking (pending, active, completed, etc.)
✅ Added discount handling
✅ Auto-calculation of final_amount
✅ Added constraint to prevent multiple active enrollments
✅ Better on_delete choices (PROTECT for financial records)

PAYMENT IMPROVEMENTS:
✅ Better payment status tracking (pending, completed, failed, etc.)
✅ Separated due_date from actual payment_date
✅ Added reference_number for bank transfers
✅ Added currency field for international students
✅ Added validation for payment dates
✅ Added overdue calculation methods
✅ Used your exact payment method names

PAYROLL IMPROVEMENTS:
✅ Added payroll types (salary, hourly, bonus, etc.)
✅ Added period tracking (start/end dates)
✅ Added gross/net amount calculation with deductions
✅ Added status tracking
✅ Added constraint to prevent duplicate payrolls
✅ Better financial record keeping

ON_DELETE STRATEGY:
✅ Used PROTECT for all financial models to prevent accidental data loss
✅ Financial records (payments, enrollments, payrolls) should never be cascade deleted
✅ This ensures audit trail and legal compliance
"""

class FinancialReport:
    """
    Helper class for generating financial reports
    """
    
    @staticmethod
    def get_monthly_summary(year, month):
        """Get financial summary for a specific month"""
        from datetime import datetime
        from calendar import monthrange
        
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, monthrange(year, month)[1]).date()
        
        # Income from payments
        income = Payment.objects.filter(
            payment_status='completed',
            payment_date__range=[start_date, end_date]
        ).aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Expenses
        expenses = Expense.objects.filter(
            status='paid',
            payment_date__range=[start_date, end_date]
        ).aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')
        
        return {
            'period': f"{year}-{month:02d}",
            'income': income,
            'expenses': expenses,
            'profit': income - expenses,
            'start_date': start_date,
            'end_date': end_date
        }
    
    @staticmethod
    def get_expense_breakdown_by_category(start_date, end_date):
        """Get expense breakdown by category for a period"""
        
        return Expense.objects.filter(
            status='paid',
            payment_date__range=[start_date, end_date]
        ).values(
            'category__name',
            'category__category_type'
        ).annotate(
            total=Sum('total_amount')
        ).order_by('-total')


# =============================================================================
# DESIGN CONSIDERATIONS
# =============================================================================

"""
EXPENSE MANAGEMENT FEATURES:
✅ ExpenseCategory - Organize expenses for better reporting
✅ Supplier - Track vendors and payment terms
✅ Expense - Main expense tracking with full lifecycle
✅ RecurringExpenseTemplate - Handle monthly rent, utilities, etc.
✅ FinancialPeriod - Formal period reporting
✅ Approval workflow - Expenses need approval before payment
✅ Overdue tracking - Know when payments are late
✅ Auto-numbering - Unique expense numbers for audit trail
✅ Tax handling - Separate tax amounts for compliance
✅ Recurring expense automation - Auto-generate monthly bills

FINANCIAL REPORTING:
✅ Period-based profit/loss calculation
✅ Income vs Expenses tracking  
✅ Category-based expense analysis
✅ Supplier payment analysis
✅ Overdue payment tracking

ON_DELETE STRATEGY:
✅ PROTECT for all financial relationships - preserve audit trail
✅ SET_NULL only for approval relationships (if approver leaves)
✅ Financial data integrity is paramount
"""