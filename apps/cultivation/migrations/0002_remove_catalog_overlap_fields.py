from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("cultivation", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(model_name="cultivationguide", name="light_needs"),
        migrations.RemoveField(model_name="cultivationguide", name="planting_medium"),
        migrations.RemoveField(model_name="cultivationguide", name="water_needs"),
    ]