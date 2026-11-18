import django.core.validators
from django.db import migrations, models


def move_text_to_notes(apps, schema_editor):
    CultivationGuide = apps.get_model("cultivation", "CultivationGuide")
    for guide in CultivationGuide.objects.all():
        guide.watering_note = guide.watering_frequency
        guide.fertilizing_note = guide.fertilizing
        guide.harvest_note = guide.harvest_time
        guide.save(update_fields=["watering_note", "fertilizing_note", "harvest_note"])


class Migration(migrations.Migration):

    dependencies = [
        ("cultivation", "0002_remove_catalog_overlap_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="cultivationguide",
            name="watering_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="fertilizing_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="harvest_note",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="is_harvestable",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="harvest_days_min",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="harvest_days_max",
            field=models.PositiveSmallIntegerField(
                blank=True,
                null=True,
                validators=[django.core.validators.MinValueValidator(1)],
            ),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="sources",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.RunPython(move_text_to_notes, migrations.RunPython.noop),
        migrations.RemoveField(model_name="cultivationguide", name="watering_frequency"),
        migrations.RemoveField(model_name="cultivationguide", name="fertilizing"),
        migrations.RemoveField(model_name="cultivationguide", name="harvest_time"),
        migrations.AddField(
            model_name="cultivationguide",
            name="watering_frequency",
            field=models.CharField(
                choices=[
                    ("daily", "Setiap hari"),
                    ("every_2_3_days", "2-3 hari sekali"),
                    ("weekly", "Seminggu sekali"),
                    ("biweekly", "Dua minggu sekali"),
                    ("when_dry", "Saat media bagian atas kering"),
                ],
                default="when_dry",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="cultivationguide",
            name="fertilizing_frequency",
            field=models.CharField(
                choices=[
                    ("weekly", "Seminggu sekali"),
                    ("biweekly", "Dua minggu sekali"),
                    ("monthly", "Sebulan sekali"),
                    ("every_3_months", "Tiga bulan sekali"),
                    ("as_needed", "Sesuai fase tumbuh"),
                    ("none", "Tidak perlu rutin"),
                ],
                default="as_needed",
                max_length=20,
            ),
        ),
    ]