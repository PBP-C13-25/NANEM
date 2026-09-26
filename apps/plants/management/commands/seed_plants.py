"""Import only the first species-list match for each curated Indonesian name."""
import json
import os
import time
from pathlib import Path

import requests
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.db.models import Q

from apps.plants.models import Plant


SEED_DIR = Path(__file__).resolve().parents[2] / "seed_data"
SEED_PATH = SEED_DIR / "plant_seed_names.json"
REPORT_PATH = SEED_DIR / "seed_report.txt"
API_URL = "https://perenual.com/api/v2/species-list"
REQUEST_DELAY = 0.75


def map_sunlight(values):
    if not isinstance(values, list):
        return ""
    mapping = {
        "full sun": "full_sun",
        "sun": "full_sun",
        "part sun/part shade": "partial_shade",
        "sun-part shade": "partial_shade",
        "partial shade": "partial_shade",
        "part shade": "partial_shade",
        "full shade": "shade",
        "shade": "shade",
    }
    choices = {
        mapping.get(" ".join(value.lower().replace("_", " ").split()))
        for value in values if isinstance(value, str)
    }
    return next((value for value in ("shade", "partial_shade", "full_sun")
                 if value in choices), "")


def map_match(entry, match):
    if not isinstance(match, dict) or type(match.get("id")) is not int:
        raise CommandError("Invalid API match: missing integer species id.")
    scientific_name = match.get("scientific_name")
    if isinstance(scientific_name, list):
        scientific_name = ", ".join(
            value.strip() for value in scientific_name
            if isinstance(value, str) and value.strip()
        )
    image = match.get("default_image")
    image_url = ""
    if isinstance(image, dict):
        image_url = next((image[key] for key in (
            "original_url", "regular_url", "medium_url", "small_url", "thumbnail"
        ) if isinstance(image.get(key), str) and image[key].strip()), "")
    fields = {
        "perenual_id": match["id"],
        "name": entry["nama_id"],
        "category": entry["category"],
        "scientific_name": scientific_name if isinstance(scientific_name, str) else "",
        "description": match.get("description") if isinstance(match.get("description"), str) else "",
        "image_url": image_url,
        "sunlight": map_sunlight(match.get("sunlight")),
    }
    # Validate lengths/URLs without inventing missing API data. The existing
    # model requires sunlight in forms, but this importer deliberately allows
    # an empty value when the API does not provide a usable one.
    for name, value in fields.items():
        if name == "sunlight" and value == "":
            continue
        try:
            Plant._meta.get_field(name).clean(value, None)
        except ValidationError:
            raise CommandError(f"Invalid or oversized API/seed field: {name}.") from None
    return fields


class Command(BaseCommand):
    help = "Seed Plant records from the curated JSON list using Perenual species-list."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, help="Only process the first N entries.")

    def load_entries(self, limit):
        if limit is not None and limit < 0:
            raise CommandError("--limit must be zero or a positive integer.")
        try:
            entries = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise CommandError(f"Cannot read a valid seed JSON file at {SEED_PATH}.") from None
        if not isinstance(entries, list):
            raise CommandError("Seed JSON must be an array of objects.")
        categories = dict(Plant.CATEGORY_CHOICES)
        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict) or any(
                not isinstance(entry.get(key), str) or not entry[key].strip()
                for key in ("nama_id", "query", "category")
            ):
                raise CommandError(f"Invalid seed entry #{index}: nama_id, query and category are required.")
            if entry["category"] not in categories or len(entry["nama_id"]) > 200:
                raise CommandError(f"Invalid name or category in seed entry #{index}.")
        return entries if limit is None else entries[:limit]

    def fetch_match(self, session, api_key, query):
        try:
            response = session.get(
                API_URL, params={"key": api_key, "q": query}, timeout=30,
                allow_redirects=False,
            )
        except requests.RequestException:
            # Request exception text can contain the URL and secret API key.
            raise CommandError("Perenual request failed (network error or timeout).") from None
        if response.status_code == 429:
            raise CommandError("Perenual rate limit reached (HTTP 429). Stop and retry later.")
        if response.status_code in (401, 403):
            raise CommandError("Perenual authentication/access denied. Check PERENUAL_API_KEY and API access.")
        if response.status_code != 200:
            raise CommandError(f"Perenual returned HTTP {response.status_code}; import stopped.")
        try:
            payload = response.json()
        except ValueError:
            raise CommandError("Perenual returned invalid JSON; import stopped.") from None
        if not isinstance(payload, dict) or payload.get("error") or payload.get("message"):
            raise CommandError("Perenual returned an API error; check API key, access and quota.")
        results = payload.get("data")
        if not isinstance(results, list):
            raise CommandError("Perenual response is missing a valid data array; import stopped.")
        if results and not isinstance(results[0], dict):
            raise CommandError("Perenual returned an invalid first match; import stopped.")
        return results[0] if results else None

    def save_match(self, fields):
        with transaction.atomic():
            candidates = list(Plant.objects.select_for_update().filter(
                Q(perenual_id=fields["perenual_id"]) | Q(name=fields["name"])
            )[:2])
            if len(candidates) > 1:
                raise CommandError("Multiple Plant records match this API id/name; resolve duplicates before retrying.")
            if candidates:
                plant = candidates[0]
                for name, value in fields.items():
                    setattr(plant, name, value)
                plant.save(update_fields=[*fields, "updated_at"])
            else:
                # Climate, space and medium support are not inferred from names.
                # Unmapped fields retain the model's existing defaults.
                Plant.objects.create(**fields)

    def handle(self, *args, **options):
        entries = self.load_entries(options.get("limit"))
        api_key = os.environ.get("PERENUAL_API_KEY", "").strip()
        if not api_key:
            raise CommandError("Set PERENUAL_API_KEY before running seed_plants.")
        processed = matched = failed = 0
        missing = []
        error = None
        with requests.Session() as session:
            for index, entry in enumerate(entries):
                if index:
                    time.sleep(REQUEST_DELAY)
                processed += 1
                try:
                    match = self.fetch_match(session, api_key, entry["query"])
                    if match is None:
                        missing.append(entry["nama_id"])
                    else:
                        self.save_match(map_match(entry, match))
                        matched += 1
                except (CommandError, DatabaseError) as exc:
                    failed = 1
                    reason = str(exc) if isinstance(exc, CommandError) else "Database write failed. Check migrations and database availability."
                    error = f"Stopped at {entry['nama_id']}: {reason}"
                    break
        report = "\n".join([
            "Plant seed report",
            f"Status: {'STOPPED' if error else 'COMPLETE'}",
            f"Selected: {len(entries)}",
            f"Total processed (attempted): {processed}",
            f"Matched and saved: {matched}",
            f"Zero results: {len(missing)}",
            f"Failed: {failed}",
            f"Not processed: {len(entries) - processed}",
            "Names with zero results:",
            *([f"- {name}" for name in missing] or ["(none)"]),
            *([error] if error else []),
        ]) + "\n"
        self.stdout.write(report)
        try:
            REPORT_PATH.write_text(report, encoding="utf-8")
        except OSError:
            raise CommandError(f"Could not save report at {REPORT_PATH}. See printed report above.") from None
        if error:
            raise CommandError(error)
