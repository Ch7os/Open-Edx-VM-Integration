from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("djangoapp", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="labdefinition",
            name="allow_extend",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="labdefinition",
            name="extend_minutes",
            field=models.PositiveIntegerField(default=30),
        ),
    ]
