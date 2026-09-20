from __future__ import annotations

import math
import re
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class CityBounds:
    city: str
    country: str
    display_name: str
    min_lat: float
    min_lng: float
    max_lat: float
    max_lng: float


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return cleaned or "location"


def geocode_city(city: str, country: str) -> CityBounds:
    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": f"{city}, {country}", "format": "json", "limit": 1},
        headers={"User-Agent": "local-business-scrape-engine/0.1"},
        timeout=30,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        raise ValueError(f"Could not find city bounds for {city}, {country}")
    row = rows[0]
    south, north, west, east = [float(value) for value in row["boundingbox"]]
    return CityBounds(
        city=city,
        country=country,
        display_name=row.get("display_name", f"{city}, {country}"),
        min_lat=south,
        min_lng=west,
        max_lat=north,
        max_lng=east,
    )


def discover_city_areas(bounds: CityBounds, limit: int = 250) -> list[dict]:
    query = f"""
    [out:json][timeout:60];
    (
      node["place"~"suburb|neighbourhood|quarter|locality"]({bounds.min_lat},{bounds.min_lng},{bounds.max_lat},{bounds.max_lng});
      way["place"~"suburb|neighbourhood|quarter|locality"]({bounds.min_lat},{bounds.min_lng},{bounds.max_lat},{bounds.max_lng});
      relation["place"~"suburb|neighbourhood|quarter|locality"]({bounds.min_lat},{bounds.min_lng},{bounds.max_lat},{bounds.max_lng});
    );
    out center tags {limit};
    """
    response = requests.post(
        "https://overpass-api.de/api/interpreter",
        data={"data": query},
        headers={"User-Agent": "local-business-scrape-engine/0.1"},
        timeout=90,
    )
    response.raise_for_status()
    seen = set()
    areas: list[dict] = []
    for element in response.json().get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name")
        if not name or name.lower() in seen:
            continue
        lat = element.get("lat") or element.get("center", {}).get("lat")
        lng = element.get("lon") or element.get("center", {}).get("lon")
        if lat is None or lng is None:
            continue
        seen.add(name.lower())
        areas.append({"name": name, "lat": float(lat), "lng": float(lng), "place": tags.get("place")})
    return sorted(areas, key=lambda row: row["name"])


def bounds_around_point(city: str, country: str, area_name: str, lat: float, lng: float, radius_km: float = 1.25) -> CityBounds:
    lat_delta = radius_km / 111.32
    lng_delta = radius_km / (111.32 * max(math.cos(math.radians(lat)), 0.01))
    return CityBounds(
        city=f"{area_name}, {city}",
        country=country,
        display_name=f"{area_name}, {city}, {country}",
        min_lat=lat - lat_delta,
        min_lng=lng - lng_delta,
        max_lat=lat + lat_delta,
        max_lng=lng + lng_delta,
    )


def bbox_area_km2(min_lat: float, min_lng: float, max_lat: float, max_lng: float) -> float:
    mid_lat = (min_lat + max_lat) / 2
    height = abs(max_lat - min_lat) * 111.32
    width = abs(max_lng - min_lng) * 111.32 * max(math.cos(math.radians(mid_lat)), 0.01)
    return height * width


def estimate_grid_cells(min_lat: float, min_lng: float, max_lat: float, max_lng: float, grid_cell_km: float) -> int:
    return max(1, math.ceil(bbox_area_km2(min_lat, min_lng, max_lat, max_lng) / (grid_cell_km * grid_cell_km)))


def auto_grid_profile(area_km2: float, intensity: str) -> dict:
    if intensity == "street_level":
        cell = 0.25 if area_km2 < 900 else 0.35
        return {"grid_cell_km": cell, "radius_meters": 450 if cell <= 0.25 else 600, "zoom": 17, "depth": 1}
    if intensity == "balanced":
        cell = 0.5 if area_km2 < 900 else 0.75
        return {"grid_cell_km": cell, "radius_meters": 700 if cell <= 0.5 else 1000, "zoom": 16, "depth": 1}
    cell = 1.0 if area_km2 < 1200 else 1.5
    return {"grid_cell_km": cell, "radius_meters": 1200 if cell <= 1.0 else 1800, "zoom": 15, "depth": 1}


def upsert_location(conn, location_id: str, bounds: CityBounds, grid_profile: str) -> None:
    conn.execute(
        """
        INSERT INTO locations (id, country, region, city, bbox_min_lat, bbox_min_lng, bbox_max_lat, bbox_max_lng, grid_profile)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
          country=excluded.country,
          city=excluded.city,
          bbox_min_lat=excluded.bbox_min_lat,
          bbox_min_lng=excluded.bbox_min_lng,
          bbox_max_lat=excluded.bbox_max_lat,
          bbox_max_lng=excluded.bbox_max_lng,
          grid_profile=excluded.grid_profile
        """,
        (
            location_id,
            bounds.country,
            None,
            bounds.city,
            bounds.min_lat,
            bounds.min_lng,
            bounds.max_lat,
            bounds.max_lng,
            grid_profile,
        ),
    )
    conn.commit()


def upsert_keyword_category(conn, keyword: str, variants: list[str] | None = None) -> str:
    category_id = slugify(keyword)
    all_variants = variants or [keyword]
    import json

    conn.execute(
        """
        INSERT INTO categories (id, canonical_name, tier, variants, enabled, default_depth, grid_profile)
        VALUES (?, ?, 1, ?, 1, 1, 'auto')
        ON CONFLICT(id) DO UPDATE SET canonical_name=excluded.canonical_name, variants=excluded.variants, enabled=1
        """,
        (category_id, keyword.title(), json.dumps(all_variants)),
    )
    conn.commit()
    return category_id
