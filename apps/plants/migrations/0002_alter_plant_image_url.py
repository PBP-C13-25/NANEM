from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("plants", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plant",
            name="image_url",
            field=models.URLField(max_length=2048, blank=True),
        ),
    ]
