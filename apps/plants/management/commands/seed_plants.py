"""Fetch resumable candidate files, then import only manually selected matches."""
import json
import os
import time
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

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
SELECTIONS_PATH = SEED_DIR / "plant_selections.json"
DETAILS_PATH = SEED_DIR / "plant_details.json"
CURATED_DETAILS_PATH = SEED_DIR / "plant_details_curated.json"
API_URL = "https://perenual.com/api/v2/species-list"
DETAILS_URL = "https://perenual.com/api/v2/species/details"
REQUEST_DELAY = 0.75
FREE_DETAILS_MAX_ID = 3000
OPTIONAL_ENRICHMENT_FIELDS = (
    "description", "image_url", "sunlight",
    "watering", "care_level", "drought_tolerant", "indoor",
)


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


def load_json_array(path, label):
    try:
        records = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise CommandError(f"Cannot read valid {label} JSON at {path}.") from None
    if not isinstance(records, list):
        raise CommandError(f"{label} must contain a JSON array.")
    return records


def load_selections(entries):
    records = load_json_array(SELECTIONS_PATH, "selection")
    if len(records) != len(entries):
        raise CommandError("Selection list must contain exactly one row per seed entry.")
    ids = set()
    cached = {row["nama_id"]: row for row in load_candidates()}
    for entry, record in zip(entries, records):
        if not isinstance(record, dict) or record.get("nama_id") != entry["nama_id"]:
            raise CommandError("Selection names/order must match the seed list.")
        status = record.get("status")
        selected = record.get("perenual_id")
        if status == "approved":
            if type(selected) is not int or selected <= 0 or selected in ids:
                raise CommandError(f"Invalid or duplicate approved Perenual id for {entry['nama_id']}.")
            candidate = cached.get(entry["nama_id"])
            if candidate and not any(item["id"] == selected for item in candidate["candidates"]):
                raise CommandError(f"{entry['nama_id']}: approved id is not in cached API candidates.")
            ids.add(selected)
        elif status == "local_only":
            if selected is not None or not isinstance(record.get("reason"), str) or not record["reason"].strip():
                raise CommandError(f"Local-only entry {entry['nama_id']} needs a reason and null Perenual id.")
        else:
            raise CommandError(f"Unknown selection status for {entry['nama_id']}.")
    return records


def load_details():
    if not DETAILS_PATH.exists():
        return []
    records = load_json_array(DETAILS_PATH, "detail cache")
    ids = set()
    for record in records:
        if not isinstance(record, dict) or type(record.get("perenual_id")) is not int:
            raise CommandError("Invalid detail cache record.")
        species_id = record["perenual_id"]
        if species_id in ids or record.get("status") not in ("complete", "unavailable", "failed"):
            raise CommandError("Duplicate id or invalid status in detail cache.")
        ids.add(species_id)
        if record["status"] == "complete" and (
            not isinstance(record.get("data"), dict) or record["data"].get("id") != species_id
        ):
            raise CommandError("Detail cache id does not match its response.")
    return records


def save_details(records):
    write_atomic(DETAILS_PATH, json.dumps(records, ensure_ascii=False, indent=2) + "\n")


def load_curated_details():
    if not CURATED_DETAILS_PATH.exists():
        return {}
    records = load_json_array(CURATED_DETAILS_PATH, "curated detail")
    result = {}
    for record in records:
        if (not isinstance(record, dict) or type(record.get("id")) is not int
                or record["id"] <= 0 or record["id"] in result):
            raise CommandError("Invalid or duplicate id in curated details.")
        if not isinstance(record.get("sunlight", []), list):
            raise CommandError("Curated sunlight must be a list.")
        if any(key in record for key in ("default_image", "image_url", "description")):
            raise CommandError("Curated details must not contain raw images or descriptions.")
        result[record["id"]] = record
    return result


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
        return []
    mapping = {
        "full sun": "full_sun",
        "full sun/part shade": "full_sun",
        "sun": "full_sun",
        "part sun/part shade": "partial_shade",
        "sun-part shade": "partial_shade",
        "partial shade": "partial_shade",
        "part shade": "partial_shade",
        "part sun": "partial_shade",
        "full shade": "shade",
        "shade": "shade",
    }
    choices = {
        mapping.get(" ".join(value.lower().replace("_", " ").split()))
        for value in values if isinstance(value, str)
    }
    return [value for value in ("full_sun", "partial_shade", "shade") if value in choices]


def stable_image_url(image):
    if not isinstance(image, dict):
        return ""
    for key in ("regular_url", "medium_url", "small_url", "original_url", "thumbnail"):
        url = image.get(key)
        if not isinstance(url, str):
            continue
        parsed = urlparse(url)
        if (parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.query
                or "upgrade_access" in parsed.path.lower()):
            continue
        return url
    return ""


def map_match(entry, selection, detail=None):
    species_id = selection["perenual_id"]
    if detail is not None and detail.get("id") != species_id:
        raise CommandError(f"{entry['nama_id']}: detail id does not match selection.")
    detail = detail or {}
    fields = {
        "perenual_id": species_id,
        "name": entry["nama_id"],
        "category": entry["category"],
        "scientific_name": entry.get("scientific_name") or "",
        "description": detail.get("description") if isinstance(detail.get("description"), str) else "",
        "image_url": stable_image_url(detail.get("default_image")),
        "sunlight": map_sunlight(detail.get("sunlight")),
        "watering": detail.get("watering") if isinstance(detail.get("watering"), str) else "",
        "care_level": detail.get("care_level") if isinstance(detail.get("care_level"), str) else "",
        "drought_tolerant": detail.get("drought_tolerant") if type(detail.get("drought_tolerant")) is bool else None,
        "indoor": detail.get("indoor") if type(detail.get("indoor")) is bool else None,
    }
    for name, value in fields.items():
        try:
            Plant._meta.get_field(name).clean(value, None)
        except ValidationError:
            raise CommandError(f"Invalid or oversized API/seed field: {name}.") from None
    return fields


class Command(BaseCommand):
    help = "Fetch species candidates/details, then import the curated manifest offline."

    def add_arguments(self, parser):
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument("--fetch", action="store_true", help="Cache first-page candidates; never write Plant records.")
        modes.add_argument("--fetch-details", action="store_true", help="Cache details for approved species on the free tier.")
        modes.add_argument("--import-selected", action="store_true", help="Import the curated manifest without API requests.")
        parser.add_argument("--refresh", action="store_true", help="Re-fetch the selected API mode.")
        parser.add_argument("--dry-run", action="store_true", help="With --import-selected, validate and report without database writes.")
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
            if entry.get("scientific_name") is not None and (
                not isinstance(entry["scientific_name"], str)
                or len(entry["scientific_name"]) > 200
            ):
                raise CommandError(f"Invalid scientific name in seed entry #{index}.")
            if entry["nama_id"] in names:
                raise CommandError(f"Duplicate nama_id in seed entry #{index}.")
            names.add(entry["nama_id"])
        return entries if limit is None else entries[:limit]

    def fetch_candidates(self, session, api_key, query):
        return self.request_json(session, API_URL, api_key, {"q": query}, expect_list=True)

    def request_json(self, session, url, api_key, extra_params, expect_list=False):
        try:
            response = session.get(
                url, params={"key": api_key, **extra_params}, timeout=30,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            # Request exception text can contain the URL and secret API key.
            raise CommandError(f"Perenual request failed ({type(exc).__name__}); rerun --fetch to resume.") from None
        # Read quota from this response only; never spend another request to check it.
        quota = []
        for header in ("X-RateLimit-Remaining", "X-RateLimit-Limit"):
            value = response.headers.get(header)
            quota.append(value if isinstance(value, str) and value.isascii() and value.isdecimal() else "tidak tersedia")
        self.stdout.write(
            f"Perenual HTTP {response.status_code} | Sisa kuota: {quota[0]} / {quota[1]} "
            "request (menurut respons ini)"
        )
        if response.status_code == 429:
            raise CommandError("Perenual rate limit reached (HTTP 429). Stop and retry later.")
        if response.status_code in (401, 403):
            raise CommandError("Perenual authentication/access denied. Check PERENUAL_API_KEY and API access.")
        if response.status_code == 404:
            if expect_list:
                raise CommandError("Perenual species-list endpoint returned HTTP 404.")
            return None
        if response.status_code != 200:
            raise CommandError(f"Perenual returned HTTP {response.status_code}; fetch stopped.")
        try:
            payload = response.json()
        except ValueError:
            raise CommandError("Perenual returned invalid JSON; import stopped.") from None
        if not isinstance(payload, dict) or payload.get("error") or payload.get("message"):
            raise CommandError("Perenual returned an API error; check API key, access and quota.")
        if expect_list:
            results = payload.get("data")
            if not isinstance(results, list):
                raise CommandError("Perenual response is missing a valid data array; fetch stopped.")
            validate_candidates(results)
        return payload

    def save_match(self, fields):
        with transaction.atomic():
            lookup = Q(name=fields["name"])
            if fields["perenual_id"] is not None:
                lookup |= Q(perenual_id=fields["perenual_id"])
            candidates = list(Plant.objects.select_for_update().filter(lookup)[:2])
            if len(candidates) > 1:
                raise CommandError("Multiple Plant records match this API id/name; resolve duplicates before retrying.")
            if candidates:
                plant = candidates[0]
                same_source = plant.perenual_id == fields["perenual_id"]
                for name, value in fields.items():
                    if (same_source and name in OPTIONAL_ENRICHMENT_FIELDS
                            and value in ("", None, [])):
                        continue
                    setattr(plant, name, value)
                plant.save(update_fields=[*fields, "updated_at"])
            else:
                # Climate, space and medium support are not inferred from names.
                # Unmapped fields retain the model's existing defaults.
                Plant.objects.create(**fields)

    def handle(self, *args, **options):
        fetch = bool(options.get("fetch"))
        fetch_details = bool(options.get("fetch_details"))
        importing = bool(options.get("import_selected"))
        if sum((fetch, fetch_details, importing)) != 1:
            raise CommandError("Choose exactly one mode: --fetch, --fetch-details or --import-selected.")
        if options.get("refresh") and importing:
            raise CommandError("--refresh requires an API fetch mode.")
        if options.get("dry_run") and not importing:
            raise CommandError("--dry-run requires --import-selected.")
        limit = options.get("limit")
        entries = self.load_entries(None)
        if limit is not None and limit < 0:
            raise CommandError("--limit must be zero or a positive integer.")
        if fetch:
            records = load_candidates()
            self.run_fetch(entries if limit is None else entries[:limit], records, options.get("refresh", False))
        else:
            selections = load_selections(entries)
            entries = entries if limit is None else entries[:limit]
            selections = selections if limit is None else selections[:limit]
            if fetch_details:
                self.run_fetch_details(selections, options.get("refresh", False))
            else:
                self.run_import(entries, selections, options.get("dry_run", False))

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

    def run_fetch_details(self, selections, refresh):
        records = load_details()
        by_id = {record["perenual_id"]: record for record in records}
        api_key = os.environ.get("PERENUAL_API_KEY", "").strip()
        fetched = reused = skipped = attempted = 0
        error = None
        with requests.Session() as session:
            for selection in selections:
                species_id = selection["perenual_id"]
                if species_id is None or species_id > FREE_DETAILS_MAX_ID:
                    skipped += 1
                    continue
                record = by_id.get(species_id)
                if record and record["status"] in ("complete", "unavailable") and not refresh:
                    reused += 1
                    continue
                if not api_key:
                    error = "Set PERENUAL_API_KEY before fetching uncached details."
                    break
                if attempted:
                    time.sleep(REQUEST_DELAY)
                attempted += 1
                try:
                    payload = self.request_json(
                        session, f"{DETAILS_URL}/{species_id}", api_key, {}
                    )
                    if payload is not None and payload.get("id") != species_id:
                        raise CommandError(f"Detail id mismatch for Perenual {species_id}.")
                    fresh = {
                        "perenual_id": species_id,
                        "status": "complete" if payload is not None else "unavailable",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "data": payload,
                    }
                    if payload is not None:
                        fetched += 1
                except CommandError as exc:
                    error = f"Stopped at Perenual {species_id}: {exc}"
                    fresh = {
                        "perenual_id": species_id, "status": "failed",
                        "fetched_at": datetime.now(timezone.utc).isoformat(),
                        "data": None,
                    }
                if record is None:
                    records.append(fresh)
                else:
                    record.clear()
                    record.update(fresh)
                by_id[species_id] = fresh
                save_details(records)
                if error:
                    break
        self.report([
            "Plant detail fetch report",
            f"Status: {'STOPPED' if error else 'COMPLETE'}",
            f"API requests attempted: {attempted}",
            f"Details cached: {fetched}",
            f"Reused from cache: {reused}",
            f"Skipped (local-only or outside free tier): {skipped}",
            "Plant database writes: 0",
        ], error)

    def run_import(self, entries, selections, dry_run):
        details = {record["perenual_id"]: record for record in load_details()}
        curated = load_curated_details()
        prepared = []
        local_only = 0
        with_details = 0
        try:
            for entry, selection in zip(entries, selections):
                species_id = selection["perenual_id"]
                if species_id is None:
                    local_only += 1
                record = details.get(species_id)
                payload = curated.get(species_id)
                if record and record["status"] == "complete":
                    payload = {**(payload or {}), **record["data"]}
                if payload is not None:
                    with_details += 1
                prepared.append(map_match(entry, selection, payload))
            if dry_run:
                with transaction.atomic():
                    # Exercise the same write path while guaranteeing rollback.
                    for fields in prepared:
                        self.save_match(fields)
                    transaction.set_rollback(True)
            elif prepared:
                with transaction.atomic():
                    for fields in prepared:
                        self.save_match(fields)
        except (CommandError, DatabaseError) as exc:
            reason = str(exc) if isinstance(exc, CommandError) else "Database write failed; check migrations and database availability."
            self.report([
                "Plant curated import report", "Status: STOPPED",
                "Imported: 0 (batch not applied)", "API requests: 0",
            ], reason)
        self.report([
            "Plant curated import report",
            f"Status: {'DRY RUN' if dry_run else 'COMPLETE'}",
            f"{'Would import' if dry_run else 'Imported'}: {len(prepared)}",
            f"Local-only: {local_only}",
            f"With Perenual id: {len(prepared) - local_only}",
            f"With plant details: {with_details}",
            "API requests: 0",
        ])
