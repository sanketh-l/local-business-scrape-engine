from __future__ import annotations

import json
import re
import uuid


def canonical_title(title: str | None) -> str | None:
    if not title:
        return None
    cleaned = re.sub(r"\b(llc|ltd|inc|co|corp)\b", "", title.lower())
    cleaned = re.sub(r"[^a-z0-9]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip() or None


def find_identity(conn, row):
    checks = [
        ("place_id", "best_place_id", row["place_id"], "place_id", 1.0),
        ("cid", "best_cid", row["cid"], "cid", 1.0),
        ("phone", "canonical_phone", row["phone"], "phone", 0.95),
        ("website_domain", "canonical_website_domain", row["website_domain"], "website_domain", 0.90),
    ]
    for _name, column, value, method, confidence in checks:
        if value:
            existing = conn.execute(f"SELECT * FROM business_identities WHERE {column} = ?", (value,)).fetchone()
            if existing:
                return existing, method, confidence
    if row["title"] and row["address"]:
        existing = conn.execute(
            "SELECT * FROM business_identities WHERE canonical_title = ? AND canonical_address = ?",
            (canonical_title(row["title"]), row["address"].lower()),
        ).fetchone()
        if existing:
            return existing, "title_address", 0.85
    return None, "new_identity", 1.0


def dedupe_all(conn) -> int:
    rows = conn.execute(
        """
        SELECT * FROM normalized_businesses n
        WHERE NOT EXISTS (SELECT 1 FROM business_sources s WHERE s.normalized_business_id = n.id)
        ORDER BY created_at
        """
    ).fetchall()
    linked = 0
    for row in rows:
        identity, method, confidence = find_identity(conn, row)
        if identity:
            identity_id = identity["id"]
        else:
            identity_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO business_identities
                (id, canonical_title, canonical_phone, canonical_website_domain, canonical_address, canonical_city,
                 canonical_region, canonical_country, canonical_latitude, canonical_longitude, best_place_id, best_cid,
                 best_google_maps_link, categories, source_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """,
                (
                    identity_id,
                    canonical_title(row["title"]),
                    row["phone"],
                    row["website_domain"],
                    row["address"].lower() if row["address"] else None,
                    row["city"],
                    row["region"],
                    row["country"],
                    row["latitude"],
                    row["longitude"],
                    row["place_id"],
                    row["cid"],
                    row["google_maps_link"],
                    json.dumps([row["category"]] if row["category"] else []),
                ),
            )
        source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{identity_id}:{row['id']}"))
        conn.execute(
            """
            INSERT OR IGNORE INTO business_sources
            (id, business_identity_id, normalized_business_id, match_method, match_confidence)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_id, identity_id, row["id"], method, confidence),
        )
        conn.execute(
            """
            UPDATE business_identities
            SET source_count = (SELECT COUNT(*) FROM business_sources WHERE business_identity_id = ?),
                last_seen_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (identity_id, identity_id),
        )
        linked += 1
    conn.commit()
    return linked
