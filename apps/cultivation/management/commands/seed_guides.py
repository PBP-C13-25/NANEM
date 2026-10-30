import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.cultivation.forms import CultivationGuideForm
from apps.cultivation.models import CultivationGuide
from apps.plants.models import Plant


DATA_FILE = Path(__file__).resolve().parents[2] / "seed_data" / "guides.json"


def build_form_data(entry):
    data = {
        "planting_steps": "\n".join(entry.get("planting_steps", [])),
        "watering_frequency": entry.get("watering_frequency", ""),
        "watering_note": entry.get("watering_note", ""),
        "fertilizing_frequency": entry.get("fertilizing_frequency", ""),
        "fertilizing_note": entry.get("fertilizing_note", ""),
        "harvest_days_min": entry.get("harvest_days_min") or "",
        "harvest_days_max": entry.get("harvest_days_max") or "",
        "harvest_note": entry.get("harvest_note", ""),
    }
    if entry.get("is_harvestable", True):
        data["is_harvestable"] = "on"
    return data


def source_errors(sources):
    if not sources:
        return ["tidak ada sumber"]
    errors = []
    for source in sources:
        if not source.get("title") or not str(source.get("url", "")).startswith(("http://", "https://")):
            errors.append(f"sumber tidak valid: {source}")
    return errors


class Command(BaseCommand):
    help = "Memuat panduan budidaya dari apps/cultivation/seed_data/guides.json."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Periksa data tanpa menyimpan.")
        parser.add_argument("--overwrite", action="store_true", help="Timpa panduan yang sudah ada.")

    def handle(self, *args, **options):
        if not DATA_FILE.exists():
            raise CommandError(f"File tidak ditemukan: {DATA_FILE}")

        entries = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        created = updated = skipped = 0
        problems = []

        for entry in entries:
            name = entry.get("plant", "")
            plant = Plant.objects.filter(name=name).first()
            if plant is None:
                problems.append(f"{name}: tanaman tidak ada di katalog")
                continue

            existing = CultivationGuide.objects.filter(plant=plant).first()
            if existing and not options["overwrite"]:
                skipped += 1
                continue

            form = CultivationGuideForm(build_form_data(entry), instance=existing)
            errors = source_errors(entry.get("sources"))
            if not form.is_valid():
                errors.extend(f"{field}: {' '.join(messages)}" for field, messages in form.errors.items())
            if errors:
                problems.append(f"{name}: " + "; ".join(errors))
                continue

            if not options["dry_run"]:
                guide = form.save(commit=False)
                guide.plant = plant
                guide.sources = entry["sources"]
                guide.save()
            if existing:
                updated += 1
            else:
                created += 1

        prefix = "[dry-run] " if options["dry_run"] else ""
        self.stdout.write(
            f"{prefix}dibuat: {created}, diperbarui: {updated}, dilewati: {skipped}, bermasalah: {len(problems)}"
        )
        for problem in problems:
            self.stderr.write(f"  - {problem}")
        if problems:
            raise CommandError("Ada data yang tidak valid.")