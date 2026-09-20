from __future__ import annotations


def coverage_report(conn, location_id: str | None = None, category_id: str | None = None) -> dict:
    filters = []
    params = []
    if location_id:
        filters.append("location_id = ?")
        params.append(location_id)
    if category_id:
        filters.append("category_id = ?")
        params.append(category_id)
    where = "WHERE " + " AND ".join(filters) if filters else ""
    task_counts = conn.execute(
        f"SELECT status, COUNT(*) count FROM scrape_tasks {where} GROUP BY status",
        params,
    ).fetchall()
    total_tasks = conn.execute(f"SELECT COUNT(*) count FROM scrape_tasks {where}", params).fetchone()["count"]
    zero_results = conn.execute(
        f"SELECT COUNT(*) count FROM scrape_tasks {where + (' AND ' if where else 'WHERE ')} status = 'completed' AND COALESCE(result_count, 0) = 0",
        params,
    ).fetchone()["count"]
    raw_rows = conn.execute("SELECT COUNT(*) count FROM raw_scrape_results").fetchone()["count"]
    normalized = conn.execute("SELECT COUNT(*) count FROM normalized_businesses").fetchone()["count"]
    unique = conn.execute("SELECT COUNT(*) count FROM business_identities").fetchone()["count"]
    duplicate_ratio = round(1 - (unique / normalized), 4) if normalized else 0
    return {
        "total_tasks": total_tasks,
        "task_status": {row["status"]: row["count"] for row in task_counts},
        "zero_result_completed_tasks": zero_results,
        "raw_rows": raw_rows,
        "normalized_rows": normalized,
        "unique_businesses": unique,
        "duplicate_ratio": duplicate_ratio,
    }
