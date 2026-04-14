from decimal import Decimal

# ============================================================================
# MATRÍCULA (ENROLLMENT FEES)
# ============================================================================
# Precios base de matrícula anual

CHILDREN_ENROLLMENT_FEE = Decimal("40.00")  # Matrícula niños (1 año)
ADULT_ENROLLMENT_FEE = Decimal("20.00")  # Matrícula adultos (1 año)


# ============================================================================
# MENSUALIDADES (MONTHLY FEES)
# ============================================================================
# Precios base mensuales según tipo de horario

FULL_TIME_MONTHLY_FEE = Decimal("54.00")  # Jornada completa (2 clases/semana)
PART_TIME_MONTHLY_FEE = Decimal("36.00")  # Media jornada (1 clase/semana)
ADULT_GROUP_MONTHLY_FEE = Decimal("60.00")  # Grupo adultos (1 clase/semana)


# ============================================================================
# DESCUENTOS (DISCOUNTS)
# ============================================================================
# Formato: (valor, tipo) donde tipo puede ser 'flat' (cantidad fija) o 'percentage' (porcentaje)

LANGUAGE_CHEQUE_DISCOUNT = (Decimal("20.00"), "flat")  # Cheque idioma
QUARTERLY_ENROLLMENT_DISCOUNT = (Decimal("5.00"), "percentage")  # Matrícula trimestral (5%)
OLD_STUDENT_DISCOUNT = (Decimal("20.00"), "flat")  # Alumno antiguo (-20€)
JUNE_DISCOUNT = (Decimal("20.00"), "flat")  # Descuento junio (completar año, NO adultos)
FULL_YEAR_BONUS = (Decimal("20.00"), "flat")  # Año completo (NO adultos)
SIBLING_DISCOUNT = (Decimal("5.00"), "percentage")  # Hermanos (5% cada mes)
HALF_MONTH_DISCOUNT = (Decimal("50.00"), "percentage")  # Medio mes (septiembre)
ONE_WEEK_DISCOUNT = (Decimal("75.00"), "percentage")  # Solo 1 semana (primer mes)
THREE_WEEK_DISCOUNT = (Decimal("25.00"), "percentage")  # Solo 3 semanas


# ============================================================================
# MONEDA (CURRENCY)
# ============================================================================

DEFAULT_CURRENCY = "EUR"


# ============================================================================
# CHOICES - Opciones para modelos
# ============================================================================

ENROLLMENT_TYPE_CHOICES = [
    ("adults", "Adults"),
    ("special", "Special"),
    ("languages_ticket", "Languages Ticket"),
    ("monthly", "Monthly"),
    ("half_month", "Half-month"),
    ("quarterly", "Quarterly"),
]

SCHEDULE_TYPE_CHOICES = [
    ("full_time", "2 días/semana"),
    ("part_time", "1 día/semana"),
    ("adult_group", "Adultos (1 día/semana)"),
]

PAYMENT_MODALITY_CHOICES = [
    ("monthly", "Mensual"),
    ("quarterly", "Trimestral"),
]

# Quarters for quarterly payments
QUARTERS = [
    {"name": "Q1", "months": [10, 11, 12], "includes_sept": True, "due_month": 10},  # Oct-Dec (+Sept)
    {"name": "Q2", "months": [1, 2, 3], "includes_sept": False, "due_month": 1},  # Jan-Mar
    {"name": "Q3", "months": [4, 5, 6], "includes_sept": False, "due_month": 4},  # Apr-Jun
]

ENROLLMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("active", "Active"),
    ("finished", "Finished"),
    ("cancelled", "Cancelled"),
    ("suspended", "Suspended"),
]

PAYMENT_METHOD_CHOICES = [
    ("cash", "Efectivo"),
    ("transfer", "Transferencia"),
    ("credit_card", "Tarjeta"),
]

PAYMENT_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("completed", "Completed"),
    ("failed", "Failed"),
    ("cancelled", "Cancelled"),
    ("refunded", "Refunded"),
]

PAYMENT_TYPE_CHOICES = [
    ("enrollment", "Enrollment Fee"),
    ("monthly", "Monthly Fee"),
    ("quarterly", "Quarterly Fee"),
    ("other", "Other"),
]


# ============================================================================
# VALIDACIONES
# ============================================================================

MIN_PAYMENT_AMOUNT = Decimal("0.01")  # Mínimo importe para pagos
MIN_ENROLLMENT_AMOUNT = Decimal("0.01")  # Mínimo importe para matrículas


# ============================================================================
# UTILIDADES
# ============================================================================


def calculate_discount(base_amount: Decimal, discount: tuple) -> Decimal:
    """
    Calcula el descuento basado en el tipo

    Args:
        base_amount: Importe base
        discount: Tupla (valor, tipo) donde tipo es 'flat' o 'percentage'

    Returns:
        Importe del descuento

    Example:
        >>> calculate_discount(Decimal('100'), (Decimal('10'), 'flat'))
        Decimal('10.00')
        >>> calculate_discount(Decimal('100'), (Decimal('5'), 'percentage'))
        Decimal('5.00')
    """
    value, discount_type = discount

    if discount_type == "flat":
        return value
    elif discount_type == "percentage":
        return base_amount * (value / Decimal("100"))
    else:
        raise ValueError(f"Tipo de descuento no válido: {discount_type}")


def get_monthly_fee_by_schedule(schedule_type: str) -> Decimal:
    """
    Obtiene la mensualidad según el tipo de horario

    Args:
        schedule_type: 'full_time', 'part_time', o 'adult_group'

    Returns:
        Importe mensual correspondiente
    """
    fees = {
        "full_time": FULL_TIME_MONTHLY_FEE,
        "part_time": PART_TIME_MONTHLY_FEE,
        "adult_group": ADULT_GROUP_MONTHLY_FEE,
    }

    return fees.get(schedule_type, FULL_TIME_MONTHLY_FEE)


def get_enrollment_fee(is_adult: bool = False) -> Decimal:
    """
    Obtiene el precio de matrícula según si es adulto o niño

    Args:
        is_adult: True si es adulto, False si es niño

    Returns:
        Importe de matrícula correspondiente
    """
    return ADULT_ENROLLMENT_FEE if is_adult else CHILDREN_ENROLLMENT_FEE
