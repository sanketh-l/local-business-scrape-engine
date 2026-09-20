from __future__ import annotations

import json
import uuid
from pathlib import Path

import pandas as pd

from .settings import EXPORT_DIR


EXPORT_COLUMNS = [
    "business_id",
    "business_name",
    "primary_category",
    "all_categories",
    "phone",
    "has_website",
    "email_addresses",
    "website",
    "google_maps_link",
    "address",
    "city",
    "region",
    "country",
    "postal_code",
    "latitude",
    "longitude",
    "rating",
    "review_count",
    "status",
    "place_id",
    "cid",
    "source_keywords",
    "source_grid_cells_count",
    "first_seen_at",
    "last_seen_at",
]


def export_businesses(conn, location_id: str | None, category_id: str | None, fmt: str, out: str | None) -> Path:
    filters = []
    params = []
    if location_id:
        filters.append("n.source_location_id = ?")
        params.append(location_id)
    if category_id:
        filters.append("n.source_category_id = ?")
        params.append(category_id)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    rows = conn.execute(
        f"""
        SELECT bi.id business_id, n.title business_name, n.category primary_category, bi.categories all_categories,
               n.phone, CASE WHEN n.website IS NOT NULL AND n.website != '' THEN 'yes' ELSE 'no' END has_website,
               n.emails email_addresses, n.website, n.google_maps_link, n.address, n.city, n.region, n.country,
               n.postal_code, n.latitude, n.longitude, n.review_rating rating, n.review_count, n.status, n.place_id,
               n.cid, GROUP_CONCAT(DISTINCT n.source_keyword) source_keywords,
               COUNT(DISTINCT n.source_grid_cell_id) source_grid_cells_count, bi.first_seen_at, bi.last_seen_at
        FROM business_identities bi
        JOIN business_sources bs ON bs.business_identity_id = bi.id
        JOIN normalized_businesses n ON n.id = bs.normalized_business_id
        {where}
        GROUP BY bi.id
        ORDER BY n.city, n.title
        """,
        params,
    ).fetchall()
    data = [dict(row) for row in rows]
    if not data:
        raise SystemExit("No deduped business rows to export yet. Run a real scrape first; dry-run mode only prints commands.")
    df = pd.DataFrame(data, columns=EXPORT_COLUMNS)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = Path(out) if out else EXPORT_DIR / f"businesses-{uuid.uuid4().hex[:8]}.{fmt}"
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "xlsx":
        df.to_excel(path, index=False)
    else:
        raise SystemExit("Format must be csv or xlsx")
    conn.execute(
        "INSERT INTO export_runs (id, export_type, filters, row_count, file_path) VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), fmt, json.dumps({"location_id": location_id, "category_id": category_id}), len(df), str(path)),
    )
    conn.commit()
    return path
