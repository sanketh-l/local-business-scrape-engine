from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from leadgen.city import auto_grid_profile, bbox_area_km2, estimate_grid_cells, geocode_city, slugify, upsert_keyword_category, upsert_location
from leadgen.coverage import coverage_report
from leadgen.db import connect, init_db
from leadgen.dedupe import dedupe_all
from leadgen.export import export_businesses
from leadgen.grid import generate_grid_from_profile
from leadgen.normalize import normalize_all
from leadgen.tasks import generate_tasks
from leadgen.worker import run_worker


def main() -> None:
    st.set_page_config(page_title="Leadgen Scrape Dashboard", layout="wide")
    st.title("Local Business Scrape Dashboard")
    st.caption("Pick a city and keyword, generate street-level grid tasks, run safely, then export CSV/XLSX.")

    init_db()
    conn = connect()

    with st.sidebar:
        st.header("Target")
        target_mode = st.selectbox("Target scope", ["Full city", "Specific area/neighborhood"])
        city = st.text_input("City", value="Bengaluru")
        area_name = st.text_input("Area/neighborhood", value="", placeholder="Example: Nandini Layout")
        country = st.text_input("Country", value="India")
        keyword = st.text_input("Business keyword/category", value="plumber")
        variants_raw = st.text_area("Keyword variants, one per line", value="plumber\nplumbing service\nplumbing contractor")
        intensity = st.selectbox(
            "Coverage intensity",
            options=["balanced", "street_level", "fast_preview"],
            format_func=lambda value: {
                "fast_preview": "Fast preview: fewer/larger squares",
                "balanced": "Balanced: good city coverage",
                "street_level": "Street-level: many small squares",
            }[value],
            index=1,
        )
        max_tasks = st.number_input("Worker limit per run", min_value=1, max_value=1000, value=1, step=1)
        dry_run = st.toggle("Dry run only", value=True)
        compliance_ack = st.checkbox("I accept legal/compliance risk for real scraping", value=False)

    if "bounds" not in st.session_state:
        st.session_state.bounds = None
    if "location_id" not in st.session_state:
        st.session_state.location_id = None
    if "category_id" not in st.session_state:
        st.session_state.category_id = None

    col_a, col_b, col_c = st.columns(3)
    if col_a.button("1. Find City Bounds", type="primary"):
        try:
            lookup_city = f"{area_name}, {city}" if target_mode == "Specific area/neighborhood" and area_name.strip() else city
            st.session_state.bounds = geocode_city(lookup_city, country)
            st.success(f"Found {st.session_state.bounds.display_name}")
        except Exception as exc:
            st.error(str(exc))

    bounds = st.session_state.bounds
    if bounds:
        area_km2 = bbox_area_km2(bounds.min_lat, bounds.min_lng, bounds.max_lat, bounds.max_lng)
        profile = auto_grid_profile(area_km2, intensity)
        estimated_cells = estimate_grid_cells(bounds.min_lat, bounds.min_lng, bounds.max_lat, bounds.max_lng, profile["grid_cell_km"])
        variants = [line.strip() for line in variants_raw.splitlines() if line.strip()]
        if keyword and keyword not in variants:
            variants.insert(0, keyword)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("City bbox area", f"{area_km2:,.0f} km²")
        m2.metric("Grid cell size", f"{profile['grid_cell_km']} km")
        m3.metric("Estimated squares", f"{estimated_cells:,}")
        m4.metric("Estimated tasks", f"{estimated_cells * max(1, len(variants)):,}")

        st.info(
            "Street-level coverage means many overlapping coordinate searches. It improves coverage versus one broad city search, "
            "but no scraper can honestly guarantee every business or every street."
        )

        map_df = pd.DataFrame([{"lat": bounds.min_lat, "lon": bounds.min_lng}, {"lat": bounds.max_lat, "lon": bounds.max_lng}])
        st.map(map_df, latitude="lat", longitude="lon", zoom=9)

        if col_b.button("2. Generate Squares And Queue"):
            location_label = f"{area_name}_{city}_{country}" if target_mode == "Specific area/neighborhood" and area_name.strip() else f"{city}_{country}"
            location_id = slugify(location_label)
            profile_name = f"auto_{intensity}"
            category_id = upsert_keyword_category(conn, keyword, variants)
            upsert_location(conn, location_id, bounds, profile_name)
            cells = generate_grid_from_profile(conn, location_id, profile_name, profile)
            tasks = generate_tasks(conn, location_id, category_id, variants=True)
            st.session_state.location_id = location_id
            st.session_state.category_id = category_id
            st.success(f"Generated {cells:,} grid squares and {tasks:,} new scrape tasks.")

    location_id = st.session_state.location_id
    category_id = st.session_state.category_id
    if location_id and category_id:
        st.divider()
        st.subheader("Queue Control")
        report = coverage_report(conn, location_id, category_id)
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Total tasks", f"{report['total_tasks']:,}")
        q2.metric("Raw rows", f"{report['raw_rows']:,}")
        q3.metric("Unique businesses", f"{report['unique_businesses']:,}")
        q4.metric("Duplicate ratio", report["duplicate_ratio"])
        st.json(report)

        run_col, norm_col, export_col = st.columns(3)
        if run_col.button("3. Run Worker Batch"):
            if not dry_run and not compliance_ack:
                st.error("Real scraping requires the compliance checkbox.")
            else:
                try:
                    processed = run_worker(conn, int(max_tasks), dry_run=dry_run, compliance_ack=compliance_ack)
                    st.success(f"Processed {processed} task(s).")
                except Exception as exc:
                    st.error(str(exc))

        if norm_col.button("4. Normalize And Dedupe"):
            normalized = normalize_all(conn)
            linked = dedupe_all(conn)
            st.success(f"Normalized {normalized:,} rows and linked {linked:,} rows.")

        export_format = export_col.selectbox("Export format", ["csv", "xlsx"])
        if export_col.button("5. Export File"):
            path = export_businesses(conn, location_id, category_id, export_format, None)
            st.success(f"Exported {path}")
            data = Path(path).read_bytes()
            export_col.download_button(
                "Download export",
                data=data,
                file_name=Path(path).name,
                mime="text/csv" if export_format == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        st.subheader("Latest Tasks")
        rows = conn.execute(
            """
            SELECT keyword, status, result_count, error_message, created_at
            FROM scrape_tasks
            WHERE location_id = ? AND category_id = ?
            ORDER BY created_at DESC
            LIMIT 50
            """,
            (location_id, category_id),
        ).fetchall()
        st.dataframe([dict(row) for row in rows], use_container_width=True)

    with st.expander("What this dashboard is doing"):
        st.write(
            "It geocodes the city to a bounding box, chooses a grid size from the city area and coverage intensity, "
            "creates overlapping coordinate cells, generates one scrape task per keyword variant per cell, and queues those tasks."
        )
        st.code(json.dumps({"recommended_first_run": {"dry_run": True, "worker_limit": 1}}, indent=2), language="json")


if __name__ == "__main__":
    main()
