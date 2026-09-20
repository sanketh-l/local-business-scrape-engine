from __future__ import annotations

import math

from .config import load_yaml


def generate_grid(conn, location_id: str, profiles_path: str) -> int:
    location = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    if not location:
        raise SystemExit(f"Unknown location: {location_id}")
    profiles = load_yaml(profiles_path).get("profiles", {})
    profile_name = location["grid_profile"]
    profile = profiles.get(profile_name)
    if not profile:
        raise SystemExit(f"Unknown grid profile: {profile_name}")

    cell_km = float(profile["grid_cell_km"])
    lat_step = cell_km / 111.32
    mid_lat = (location["bbox_min_lat"] + location["bbox_max_lat"]) / 2
    lng_step = cell_km / (111.32 * max(math.cos(math.radians(mid_lat)), 0.01))

    count = 0
    lat = location["bbox_min_lat"] + lat_step / 2
    row = 0
    while lat <= location["bbox_max_lat"]:
        lng = location["bbox_min_lng"] + lng_step / 2
        col = 0
        while lng <= location["bbox_max_lng"]:
            cell_id = f"{location_id}:{profile_name}:{row}:{col}"
            conn.execute(
                """
                INSERT OR IGNORE INTO grid_cells
                (id, location_id, center_lat, center_lng, bbox_min_lat, bbox_min_lng, bbox_max_lat, bbox_max_lng,
                 grid_cell_km, radius_meters, zoom, density_profile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cell_id,
                    location_id,
                    lat,
                    lng,
                    lat - lat_step / 2,
                    lng - lng_step / 2,
                    lat + lat_step / 2,
                    lng + lng_step / 2,
                    cell_km,
                    int(profile["radius_meters"]),
                    int(profile["zoom"]),
                    profile_name,
                ),
            )
            count += 1
            lng += lng_step
            col += 1
        lat += lat_step
        row += 1
    conn.commit()
    return count


def generate_grid_from_profile(conn, location_id: str, profile_name: str, profile: dict) -> int:
    location = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
    if not location:
        raise SystemExit(f"Unknown location: {location_id}")

    cell_km = float(profile["grid_cell_km"])
    lat_step = cell_km / 111.32
    mid_lat = (location["bbox_min_lat"] + location["bbox_max_lat"]) / 2
    lng_step = cell_km / (111.32 * max(math.cos(math.radians(mid_lat)), 0.01))

    conn.execute("DELETE FROM grid_cells WHERE location_id = ? AND density_profile = ?", (location_id, profile_name))
    count = 0
    lat = location["bbox_min_lat"] + lat_step / 2
    row = 0
    while lat <= location["bbox_max_lat"]:
        lng = location["bbox_min_lng"] + lng_step / 2
        col = 0
        while lng <= location["bbox_max_lng"]:
            cell_id = f"{location_id}:{profile_name}:{row}:{col}"
            conn.execute(
                """
                INSERT INTO grid_cells
                (id, location_id, center_lat, center_lng, bbox_min_lat, bbox_min_lng, bbox_max_lat, bbox_max_lng,
                 grid_cell_km, radius_meters, zoom, density_profile)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cell_id,
                    location_id,
                    lat,
                    lng,
                    lat - lat_step / 2,
                    lng - lng_step / 2,
                    lat + lat_step / 2,
                    lng + lng_step / 2,
                    cell_km,
                    int(profile["radius_meters"]),
                    int(profile["zoom"]),
                    profile_name,
                ),
            )
            count += 1
            lng += lng_step
            col += 1
        lat += lat_step
        row += 1
    conn.commit()
    return count
