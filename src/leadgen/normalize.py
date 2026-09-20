from __future__ import annotations

import json
import re
import uuid

import phonenumbers
import tldextract


def normalize_phone(phone: str | None, country: str | None = None) -> str | None:
    if not phone:
        return None
    try:
        parsed = phonenumbers.parse(phone, country if country and len(country) == 2 else None)
        if phonenumbers.is_possible_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    digits = re.sub(r"\D+", "", phone)
    return digits or None


def normalize_domain(website: str | None) -> str | None:
    if not website:
        return None
    ext = tldextract.extract(website)
    if not ext.domain or not ext.suffix:
        return None
    return f"{ext.domain}.{ext.suffix}".lower()


def normalize_text(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"\s+", " ", value.strip())


def normalize_all(conn) -> int:
    rows = conn.execute(
        """
        SELECT r.*, t.category_id, t.keyword, t.location_id, t.grid_cell_id, l.country, l.region, l.city
        FROM raw_scrape_results r
        JOIN scrape_tasks t ON t.id = r.scrape_task_id
        JOIN locations l ON l.id = t.location_id
        WHERE NOT EXISTS (SELECT 1 FROM normalized_businesses n WHERE n.raw_result_id = r.id)
        """
    ).fetchall()
    count = 0
    for row in rows:
        raw = json.loads(row["raw_json"])
        title = normalize_text(raw.get("title") or raw.get("name"))
        website = normalize_text(raw.get("website"))
        phone = normalize_phone(raw.get("phone"), row["country"])
        norm_id = str(uuid.uuid5(uuid.NAMESPACE_URL, row["id"]))
        conn.execute(
            """
            INSERT INTO normalized_businesses
            (id, raw_result_id, title, category, address, city, region, country, phone, website, website_domain,
             google_maps_link, place_id, cid, data_id, latitude, longitude, review_count, review_rating, status,
             open_hours, emails, source_category_id, source_keyword, source_location_id, source_grid_cell_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                norm_id,
                row["id"],
                title,
                raw.get("category"),
                normalize_text(raw.get("address")),
                row["city"],
                row["region"],
                row["country"],
                phone,
                website,
                normalize_domain(website),
                raw.get("link") or raw.get("google_maps_link"),
                raw.get("place_id"),
                raw.get("cid"),
                raw.get("data_id"),
                raw.get("latitude"),
                raw.get("longitude"),
                raw.get("review_count"),
                raw.get("review_rating") or raw.get("rating"),
                raw.get("status"),
                json.dumps(raw.get("open_hours")),
                json.dumps(raw.get("emails")),
                row["category_id"],
                row["keyword"],
                row["location_id"],
                row["grid_cell_id"],
            ),
        )
        count += 1
    conn.commit()
    return count
