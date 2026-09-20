from __future__ import annotations

import json
import uuid


def generate_tasks(conn, location_id: str, category_id: str, variants: bool = False) -> int:
    category = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if not category:
        raise SystemExit(f"Unknown category: {category_id}")
    cells = conn.execute("SELECT * FROM grid_cells WHERE location_id = ?", (location_id,)).fetchall()
    if not cells:
        raise SystemExit(f"No grid cells for {location_id}; run generate-grid first")

    keywords = json.loads(category["variants"])
    if not variants:
        keywords = keywords[:1]

    created = 0
    for cell in cells:
        for keyword in keywords:
            task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{category_id}:{location_id}:{cell['id']}:{keyword}"))
            before = conn.total_changes
            conn.execute(
                """
                INSERT OR IGNORE INTO scrape_tasks
                (id, category_id, location_id, grid_cell_id, keyword, depth, zoom, radius_meters)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (task_id, category_id, location_id, cell["id"], keyword, category["default_depth"], cell["zoom"], cell["radius_meters"]),
            )
            if conn.total_changes > before:
                created += 1
    conn.commit()
    return created
