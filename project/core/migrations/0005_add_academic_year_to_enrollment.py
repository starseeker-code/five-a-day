from django.db import migrations, models
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_populate_enrollment_types'),
    ]

    operations = [
        migrations.AddField(
            model_name='enrollment',
            name='academic_year',
            field=models.CharField(default=core.models.current_academic_year, max_length=9),
        ),
    ]
