# Generated manually on 2026-01-05

from django.db import migrations
from decimal import Decimal


def create_enrollment_types(apps, schema_editor):
    """
    Crea los tipos de matrícula iniciales con sus precios.
    """
    EnrollmentType = apps.get_model('core', 'EnrollmentType')
    
    enrollment_types = [
        {
            'name': 'adults',
            'display_name': 'Adultos',
            'base_amount_full_time': Decimal('60.00'),
            'base_amount_part_time': Decimal('60.00'),
            'description': 'Matrícula para grupos de adultos',
            'active': True,
        },
        {
            'name': 'special',
            'display_name': 'Especial',
            'base_amount_full_time': Decimal('0.00'),
            'base_amount_part_time': Decimal('0.00'),
            'description': 'Matrícula con precio personalizado',
            'active': True,
        },
        {
            'name': 'languages_ticket',
            'display_name': 'Cheque Idiomas',
            'base_amount_full_time': Decimal('54.00'),
            'base_amount_part_time': Decimal('36.00'),
            'description': 'Matrícula con cheque de idiomas (descuento aplicado)',
            'active': True,
        },
        {
            'name': 'monthly',
            'display_name': 'Mensual',
            'base_amount_full_time': Decimal('54.00'),
            'base_amount_part_time': Decimal('36.00'),
            'description': 'Pago mensual estándar',
            'active': True,
        },
        {
            'name': 'half_month',
            'display_name': 'Medio Mes',
            'base_amount_full_time': Decimal('27.00'),
            'base_amount_part_time': Decimal('18.00'),
            'description': 'Pago correspondiente a medio mes (septiembre)',
            'active': True,
        },
        {
            'name': 'quarterly',
            'display_name': 'Trimestral',
            'base_amount_full_time': Decimal('162.00'),  # 54 * 3
            'base_amount_part_time': Decimal('108.00'),  # 36 * 3
            'description': 'Pago trimestral (3 meses)',
            'active': True,
        },
    ]
    
    for enrollment_type_data in enrollment_types:
        EnrollmentType.objects.get_or_create(
            name=enrollment_type_data['name'],
            defaults={
                'display_name': enrollment_type_data['display_name'],
                'base_amount_full_time': enrollment_type_data['base_amount_full_time'],
                'base_amount_part_time': enrollment_type_data['base_amount_part_time'],
                'description': enrollment_type_data['description'],
                'active': enrollment_type_data['active'],
            }
        )


def reverse_create_enrollment_types(apps, schema_editor):
    """
    Elimina los tipos de matrícula creados.
    """
    EnrollmentType = apps.get_model('core', 'EnrollmentType')
    EnrollmentType.objects.filter(
        name__in=['adults', 'special', 'languages_ticket', 'monthly', 'half_month', 'quarterly']
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_populate_site_configuration'),
    ]

    operations = [
        migrations.RunPython(create_enrollment_types, reverse_create_enrollment_types),
    ]
