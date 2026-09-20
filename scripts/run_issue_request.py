from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

from leadgen.city import (
    auto_grid_profile,
    bbox_area_km2,
    bounds_around_point,
    discover_city_areas,
    geocode_city,
    slugify,
    upsert_keyword_category,
    upsert_location,
)
from leadgen.coverage import coverage_report
from leadgen.db import connect, init_db
from leadgen.dedupe import dedupe_all
from leadgen.export import export_businesses
from leadgen.grid import generate_grid_from_profile
from leadgen.normalize import normalize_all
from leadgen.tasks import generate_tasks
from leadgen.worker import run_worker


def parse_issue_form(body: str) -> dict[str, str]:
    values: dict[str, str] = {}
    parts = re.split(r"\n###\s+", "\n" + body)
    for part in parts:
        if not part.strip():
            continue
        lines = part.strip().splitlines()
        key = lines[0].strip().lower().replace(" ", "_").replace("?", "")
        value = "\n".join(line for line in lines[1:] if line.strip() and line.strip() != "_No response_").strip()
        values[key] = value
    return values


def truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"yes", "true", "y", "1", "i_accept_legal_risk"}


def main() -> None:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        raise SystemExit("GITHUB_EVENT_PATH is required")
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event["issue"]
    form = parse_issue_form(issue.get("body", ""))

    city = form.get("city", "Bengaluru").strip()
    country = form.get("country", "India").strip()
    area = form.get("area/neighborhood_optional", "").strip()
    category = form.get("category", "plumber").strip()
    intensity_label = form.get("coverage_intensity", "Street-level")
    intensity = "street_level" if "street" in intensity_label.lower() else "balanced" if "balanced" in intensity_label.lower() else "fast_preview"
    dry_run = "yes" not in form.get("run_real_scrape", "").lower()
    compliance_ack = truthy(form.get("legal/compliance_acknowledgement"))
    max_areas = int(re.sub(r"\D+", "", form.get("max_areas_to_queue", "50")) or 50)
    worker_limit = int(re.sub(r"\D+", "", form.get("worker_task_limit_this_run", "1")) or 1)
    variants = [category]

    init_db()
    conn = connect()

    root_bounds = geocode_city(f"{area}, {city}" if area else city, country)
    discovered_areas = [] if area else discover_city_areas(root_bounds, limit=max_areas)
    area_rows = discovered_areas or [{"name": area or city, "lat": (root_bounds.min_lat + root_bounds.max_lat) / 2, "lng": (root_bounds.min_lng + root_bounds.max_lng) / 2, "place": "city"}]

    exports_dir = Path("data/exports")
    exports_dir.mkdir(parents=True, exist_ok=True)
    areas_path = exports_dir / f"areas-{slugify(city)}-{slugify(category)}.csv"
    pd.DataFrame(area_rows).to_csv(areas_path, index=False)

    category_id = upsert_keyword_category(conn, category, variants)
    total_cells = 0
    total_tasks = 0
    queued_locations: list[str] = []
    profile_name = f"auto_{intensity}"

    for row in area_rows[:max_areas]:
        if area:
            bounds = root_bounds
            location_label = f"{area}_{city}_{country}"
        elif row.get("place") == "city" and row["name"] == city:
            bounds = root_bounds
            location_label = f"{city}_{country}"
        else:
            bounds = bounds_around_point(city, country, row["name"], float(row["lat"]), float(row["lng"]), radius_km=1.25)
            location_label = f"{row['name']}_{city}_{country}"
        location_id = slugify(location_label)
        profile = auto_grid_profile(bbox_area_km2(bounds.min_lat, bounds.min_lng, bounds.max_lat, bounds.max_lng), intensity)
        upsert_location(conn, location_id, bounds, profile_name)
        total_cells += generate_grid_from_profile(conn, location_id, profile_name, profile)
        total_tasks += generate_tasks(conn, location_id, category_id, variants=True)
        queued_locations.append(location_id)

    processed = run_worker(conn, worker_limit, dry_run=dry_run, compliance_ack=compliance_ack)
    normalized = normalize_all(conn) if not dry_run else 0
    linked = dedupe_all(conn) if not dry_run else 0
    unique = conn.execute("SELECT COUNT(*) count FROM business_identities").fetchone()["count"]
    export_path = None
    if unique:
        export_path = export_businesses(conn, None, category_id, "csv", str(exports_dir / f"{slugify(city)}-{slugify(category)}.csv"))

    summary = [
        "## Scrape Request Status",
        f"City: `{city}`",
        f"Country: `{country}`",
        f"Area: `{area or 'ALL discovered areas'}`",
        f"Category: `{category}`",
        f"Dry run: `{dry_run}`",
        f"Areas discovered/queued: `{len(area_rows[:max_areas])}`",
        f"Grid squares generated: `{total_cells}`",
        f"New tasks generated: `{total_tasks}`",
        f"Worker tasks processed this run: `{processed}`",
        f"Normalized rows: `{normalized}`",
        f"Deduped links: `{linked}`",
        f"Unique businesses: `{unique}`",
        f"Areas CSV: `{areas_path}`",
    ]
    if export_path:
        summary.append(f"Business export: `{export_path}`")
    else:
        summary.append("Business export: not created because there are no real scraped rows yet. Dry-run mode does not create leads.")
    summary.append("\nArtifacts are attached to this workflow run under `leadgen-issue-output`.")
    Path("data/summary.md").write_text("\n".join(summary), encoding="utf-8")
    print("\n".join(summary))


if __name__ == "__main__":
    main()
