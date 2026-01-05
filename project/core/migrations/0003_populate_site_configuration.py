# Generated manually on 2026-01-05

from django.db import migrations
from decimal import Decimal


def create_initial_config(apps, schema_editor):
    """
    Crea el registro inicial de SiteConfiguration con los valores por defecto.
    """
    SiteConfiguration = apps.get_model('core', 'SiteConfiguration')
    
    # Solo crear si no existe
    if not SiteConfiguration.objects.filter(pk=1).exists():
        SiteConfiguration.objects.create(
            pk=1,
            children_enrollment_fee=Decimal('40.00'),
            adult_enrollment_fee=Decimal('20.00'),
            full_time_monthly_fee=Decimal('54.00'),
            part_time_monthly_fee=Decimal('36.00'),
            adult_group_monthly_fee=Decimal('60.00'),
        )


def reverse_create_initial_config(apps, schema_editor):
    """
    Elimina el registro inicial de SiteConfiguration.
    """
    SiteConfiguration = apps.get_model('core', 'SiteConfiguration')
    SiteConfiguration.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_site_configuration'),
    ]

    operations = [
        migrations.RunPython(create_initial_config, reverse_create_initial_config),
    ]
