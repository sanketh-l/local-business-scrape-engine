from __future__ import annotations

import json
from pathlib import Path

import yaml


def load_yaml(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_config(conn, categories_path: str, locations_path: str) -> None:
    categories = load_yaml(categories_path).get("categories", [])
    locations = load_yaml(locations_path).get("locations", [])
    for category in categories:
        conn.execute(
            """
            INSERT INTO categories (id, canonical_name, tier, variants, enabled, default_depth, grid_profile)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              canonical_name=excluded.canonical_name,
              tier=excluded.tier,
              variants=excluded.variants,
              enabled=excluded.enabled,
              default_depth=excluded.default_depth,
              grid_profile=excluded.grid_profile
            """,
            (
                category["id"],
                category["canonical_name"],
                int(category.get("tier", 1)),
                json.dumps(category.get("variants", [])),
                1 if category.get("enabled", True) else 0,
                int(category.get("default_depth", 1)),
                category.get("grid_profile", "normal_city"),
            ),
        )
    for location in locations:
        bbox = location["bbox"]
        conn.execute(
            """
            INSERT INTO locations (id, country, region, city, bbox_min_lat, bbox_min_lng, bbox_max_lat, bbox_max_lng, grid_profile)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              country=excluded.country,
              region=excluded.region,
              city=excluded.city,
              bbox_min_lat=excluded.bbox_min_lat,
              bbox_min_lng=excluded.bbox_min_lng,
              bbox_max_lat=excluded.bbox_max_lat,
              bbox_max_lng=excluded.bbox_max_lng,
              grid_profile=excluded.grid_profile
            """,
            (
                location["id"],
                location["country"],
                location.get("region"),
                location["city"],
                float(bbox["min_lat"]),
                float(bbox["min_lng"]),
                float(bbox["max_lat"]),
                float(bbox["max_lng"]),
                location.get("grid_profile", "normal_city"),
            ),
        )
    conn.commit()
