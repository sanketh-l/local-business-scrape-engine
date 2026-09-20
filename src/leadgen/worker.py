from __future__ import annotations

import hashlib
import json
import subprocess
import uuid
from pathlib import Path

from .settings import RAW_DIR, REQUIRE_COMPLIANCE_ACK, SCRAPER_BIN


def build_command(task, cell, query_file: Path, output_file: Path) -> list[str]:
    return [
        SCRAPER_BIN,
        "-input",
        str(query_file),
        "-results",
        str(output_file),
        "-json",
        "-geo",
        f"{cell['center_lat']},{cell['center_lng']}",
        "-zoom",
        str(task["zoom"]),
        "-radius",
        str(task["radius_meters"]),
        "-depth",
        str(task["depth"]),
    ]


def ingest_output(conn, task_id: str, output_file: Path) -> int:
    if not output_file.exists() or output_file.stat().st_size == 0:
        return 0
    text = output_file.read_text(encoding="utf-8")
    try:
        parsed = json.loads(text)
        rows = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    count = 0
    for raw in rows:
        raw_json = json.dumps(raw, sort_keys=True)
        raw_hash = hashlib.sha256(raw_json.encode("utf-8")).hexdigest()
        raw_id = str(uuid.uuid5(uuid.NAMESPACE_URL, raw_hash))
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO raw_scrape_results
            (id, scrape_task_id, provider, raw_json, raw_hash, extracted_place_id, extracted_cid, extracted_data_id,
             extracted_title, extracted_phone, extracted_website, extracted_latitude, extracted_longitude)
            VALUES (?, ?, 'gosom_google_maps_scraper', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                raw_id,
                task_id,
                raw_json,
                raw_hash,
                raw.get("place_id"),
                raw.get("cid"),
                raw.get("data_id"),
                raw.get("title") or raw.get("name"),
                raw.get("phone"),
                raw.get("website"),
                raw.get("latitude"),
                raw.get("longitude"),
            ),
        )
        if conn.total_changes > before:
            count += 1
    conn.commit()
    return count


def run_worker(conn, limit: int, dry_run: bool = False, compliance_ack: bool = False) -> int:
    if REQUIRE_COMPLIANCE_ACK and not dry_run and not compliance_ack:
        raise SystemExit("Compliance acknowledgement required. Re-run with --compliance-ack after legal review.")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    tasks = conn.execute(
        "SELECT * FROM scrape_tasks WHERE status IN ('pending', 'failed') ORDER BY priority, created_at LIMIT ?",
        (limit,),
    ).fetchall()
    ran = 0
    for task in tasks:
        cell = conn.execute("SELECT * FROM grid_cells WHERE id = ?", (task["grid_cell_id"],)).fetchone()
        task_dir = RAW_DIR / task["id"]
        task_dir.mkdir(parents=True, exist_ok=True)
        query_file = task_dir / "query.txt"
        output_file = task_dir / "results.json"
        query_file.write_text(task["keyword"] + "\n", encoding="utf-8")
        command = build_command(task, cell, query_file, output_file)
        if dry_run:
            print(" ".join(command))
            ran += 1
            continue
        conn.execute(
            "UPDATE scrape_tasks SET status = 'running', attempt_count = attempt_count + 1, started_at = CURRENT_TIMESTAMP WHERE id = ?",
            (task["id"],),
        )
        conn.commit()
        try:
            subprocess.run(command, check=True, cwd=Path.cwd())
            result_count = ingest_output(conn, task["id"], output_file)
            conn.execute(
                "UPDATE scrape_tasks SET status = 'completed', completed_at = CURRENT_TIMESTAMP, raw_output_path = ?, result_count = ? WHERE id = ?",
                (str(output_file), result_count, task["id"]),
            )
        except Exception as exc:
            conn.execute(
                "UPDATE scrape_tasks SET status = 'failed', error_message = ? WHERE id = ?",
                (str(exc), task["id"]),
            )
        conn.commit()
        ran += 1
    return ran
