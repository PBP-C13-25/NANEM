"""Fetch resumable candidate files, then import only manually selected matches."""
import json
import os
import time
import tempfile
from datetime import datetime, timezone
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
CANDIDATES_PATH = SEED_DIR / "plant_candidates.json"
API_URL = "https://perenual.com/api/v2/species-list"
REQUEST_DELAY = 0.75


def write_atomic(path, text):
    """Replace a file only after the complete new contents have been written."""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False,
        ) as output:
            temporary = Path(output.name)
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    except OSError:
        raise CommandError(f"Cannot save {path}; check directory access and disk space.") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def save_candidates(records):
    write_atomic(CANDIDATES_PATH, json.dumps(records, ensure_ascii=False, indent=2) + "\n")


def validate_candidates(candidates):
    if not isinstance(candidates, list) or any(
        not isinstance(item, dict) or type(item.get("id")) is not int
        for item in candidates
    ):
        raise CommandError("Invalid candidates: expected objects with integer species ids.")
    ids = [item["id"] for item in candidates]
    if len(ids) != len(set(ids)):
        raise CommandError("Duplicate species ids in candidate list.")


def load_candidates():
    if not CANDIDATES_PATH.exists():
        return []
    try:
        records = json.loads(CANDIDATES_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CommandError(f"Cannot read valid JSON at {CANDIDATES_PATH}; existing file was not overwritten.") from None
    if not isinstance(records, list):
        raise CommandError("Candidate file must contain an array of records.")
    names = set()
    for record in records:
        if not isinstance(record, dict) or any(
            not isinstance(record.get(key), str) or not record[key].strip()
            for key in ("nama_id", "query", "source_url", "status")
        ):
            raise CommandError("Invalid candidate record metadata.")
        if record["nama_id"] in names:
            raise CommandError("Duplicate nama_id in candidate file.")
        names.add(record["nama_id"])
        validate_candidates(record.get("candidates"))
        if record["status"] not in ("pending", "failed", "needs_review", "no_results"):
            raise CommandError("Unknown candidate record status.")
        if (record["status"] == "no_results" and record["candidates"]) or (
            record["status"] == "needs_review" and not record["candidates"]
        ):
            raise CommandError("Candidate status does not match its results.")
    return records


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
    help = "Fetch Perenual candidates for review, or import selected cached matches offline."

    def add_arguments(self, parser):
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--fetch", action="store_true", help="Cache first-page candidates; never write Plant records.")
        modes.add_argument("--import-selected", action="store_true", help="Import only reviewed selections; never call the API.")
        parser.add_argument("--refresh", action="store_true", help="With --fetch, re-fetch and clear old selections for the limited entries.")
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
        names = set()
        for index, entry in enumerate(entries, 1):
            if not isinstance(entry, dict) or any(
                not isinstance(entry.get(key), str) or not entry[key].strip()
                for key in ("nama_id", "query", "category")
            ):
                raise CommandError(f"Invalid seed entry #{index}: nama_id, query and category are required.")
            if entry["category"] not in categories or len(entry["nama_id"]) > 200:
                raise CommandError(f"Invalid name or category in seed entry #{index}.")
            if entry["nama_id"] in names:
                raise CommandError(f"Duplicate nama_id in seed entry #{index}.")
            names.add(entry["nama_id"])
        return entries if limit is None else entries[:limit]

    def fetch_candidates(self, session, api_key, query):
        try:
            response = session.get(
                API_URL, params={"key": api_key, "q": query}, timeout=30,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            # Request exception text can contain the URL and secret API key.
            raise CommandError(f"Perenual request failed ({type(exc).__name__}); rerun --fetch to resume.") from None
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
        validate_candidates(results)
        return payload

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
        fetch = bool(options.get("fetch"))
        importing = bool(options.get("import_selected"))
        if fetch == importing:
            raise CommandError("Choose exactly one mode: --fetch or --import-selected.")
        if options.get("refresh") and not fetch:
            raise CommandError("--refresh can only be used with --fetch.")
        entries = self.load_entries(options.get("limit"))
        records = load_candidates()
        if fetch:
            self.run_fetch(entries, records, options.get("refresh", False))
        else:
            self.run_import(entries, records)

    def report(self, lines, error=None):
        text = "\n".join([*lines, *([error] if error else [])]) + "\n"
        self.stdout.write(text)
        write_atomic(REPORT_PATH, text)
        if error:
            raise CommandError(error)

    def run_fetch(self, entries, records, refresh):
        by_name = {record["nama_id"]: record for record in records}
        api_key = os.environ.get("PERENUAL_API_KEY", "").strip()
        processed = fetched = reused = calls = 0
        missing = []
        error = None
        with requests.Session() as session:
            for entry in entries:
                processed += 1
                record = by_name.get(entry["nama_id"])
                if not refresh and record and (
                    record["query"] == entry["query"]
                    and record["source_url"] == API_URL
                    and record["status"] in ("needs_review", "no_results")
                ):
                    reused += 1
                    if not record["candidates"]:
                        missing.append(entry["nama_id"])
                    continue
                # Invalidate an old selection BEFORE requesting a changed query.
                # A timeout must never leave an old selection importable.
                fresh = {
                    **entry, "source_url": API_URL, "status": "pending",
                    "fetched_at": None, "candidates": [],
                    "selected_perenual_id": None, "pagination": {},
                }
                if record is None:
                    records.append(fresh)
                    by_name[entry["nama_id"]] = fresh
                    record = fresh
                else:
                    record.clear()
                    record.update(fresh)
                save_candidates(records)
                try:
                    if not api_key:
                        raise CommandError("Set PERENUAL_API_KEY before fetching uncached queries.")
                    if calls:
                        time.sleep(REQUEST_DELAY)
                    calls += 1
                    payload = self.fetch_candidates(session, api_key, entry["query"])
                    record.update(
                        candidates=payload["data"],
                        status="needs_review" if payload["data"] else "no_results",
                        fetched_at=datetime.now(timezone.utc).isoformat(),
                        pagination={key: payload[key] for key in (
                            "current_page", "last_page", "per_page", "total"
                        ) if key in payload},
                    )
                    fetched += 1
                    if not record["candidates"]:
                        missing.append(entry["nama_id"])
                except CommandError as exc:
                    error = f"Stopped at {entry['nama_id']}: {exc}"
                    record.update(status="failed", error=str(exc))
                save_candidates(records)
                if error:
                    break
        self.report([
            "Plant candidate fetch report (first page per query)",
            f"Status: {'STOPPED' if error else 'COMPLETE'}",
            f"Selected: {len(entries)}",
            f"Total processed (attempted): {processed}",
            f"API requests attempted: {calls}",
            f"Fetched and cached: {fetched}",
            f"Reused from cache: {reused}",
            f"Zero results: {len(missing)}",
            f"Failed: {int(error is not None)}",
            f"Not processed: {len(entries) - processed}",
            "Plant database writes: 0",
            "Names with zero results:",
            *([f"- {name}" for name in missing] or ["(none)"]),
        ], error)

    def run_import(self, entries, records):
        by_name = {record["nama_id"]: record for record in records}
        prepared = []
        selected_ids = set()
        skipped = []
        # Validate every selection before any database writes.
        try:
            for entry in entries:
                record = by_name.get(entry["nama_id"])
                if record is None or record.get("selected_perenual_id") is None:
                    skipped.append(entry["nama_id"])
                    continue
                if record["query"] != entry["query"] or record["source_url"] != API_URL:
                    raise CommandError(f"{entry['nama_id']}: query/source changed; fetch and review again.")
                selected = record["selected_perenual_id"]
                if record["status"] != "needs_review" or type(selected) is not int:
                    raise CommandError(f"{entry['nama_id']}: select an integer id from a completed candidate list.")
                match = next((item for item in record["candidates"] if item["id"] == selected), None)
                if match is None:
                    raise CommandError(f"{entry['nama_id']}: selected id is not in its cached candidates.")
                if selected in selected_ids:
                    raise CommandError("The same species id was selected for multiple names; resolve before import.")
                selected_ids.add(selected)
                prepared.append(map_match(entry, match))
            if prepared:
                # Roll back the entire batch if a conflict or write error occurs.
                with transaction.atomic():
                    for fields in prepared:
                        self.save_match(fields)
        except (CommandError, DatabaseError) as exc:
            reason = str(exc) if isinstance(exc, CommandError) else "Database write failed; check migrations and database availability."
            self.report([
                "Plant selected import report", "Status: STOPPED",
                "Imported: 0 (batch not applied)", "API requests: 0",
            ], reason)
        self.report([
            "Plant selected import report", "Status: COMPLETE",
            f"Imported: {len(prepared)}", f"Skipped (not selected): {len(skipped)}",
            "API requests: 0", "Names not selected:",
            *([f"- {name}" for name in skipped] or ["(none)"]),
        ])
