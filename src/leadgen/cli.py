from __future__ import annotations

import argparse
import json

from .config import load_config
from .coverage import coverage_report
from .db import connect, init_db
from .dedupe import dedupe_all
from .export import export_businesses
from .grid import generate_grid
from .normalize import normalize_all
from .tasks import generate_tasks
from .worker import run_worker


def main() -> None:
    parser = argparse.ArgumentParser(prog="leadgen")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db")

    load = sub.add_parser("load-config")
    load.add_argument("--categories", required=True)
    load.add_argument("--locations", required=True)

    grid = sub.add_parser("generate-grid")
    grid.add_argument("--location", required=True)
    grid.add_argument("--profiles", default="configs/grid_profiles.yaml")

    tasks = sub.add_parser("generate-tasks")
    tasks.add_argument("--location", required=True)
    tasks.add_argument("--category", required=True)
    tasks.add_argument("--variants", action="store_true")

    worker = sub.add_parser("worker")
    worker.add_argument("--limit", type=int, default=1)
    worker.add_argument("--dry-run", action="store_true")
    worker.add_argument("--compliance-ack", action="store_true")

    sub.add_parser("normalize")
    sub.add_parser("dedupe")

    coverage = sub.add_parser("coverage")
    coverage.add_argument("--location")
    coverage.add_argument("--category")

    export = sub.add_parser("export")
    export.add_argument("--location")
    export.add_argument("--category")
    export.add_argument("--format", choices=["csv", "xlsx"], default="csv")
    export.add_argument("--out")

    args = parser.parse_args()

    if args.command == "init-db":
        init_db()
        print("Initialized database")
        return

    with connect() as conn:
        if args.command == "load-config":
            load_config(conn, args.categories, args.locations)
            print("Loaded config")
        elif args.command == "generate-grid":
            print(f"Generated/verified {generate_grid(conn, args.location, args.profiles)} grid cells")
        elif args.command == "generate-tasks":
            print(f"Generated {generate_tasks(conn, args.location, args.category, args.variants)} scrape tasks")
        elif args.command == "worker":
            print(f"Processed {run_worker(conn, args.limit, args.dry_run, args.compliance_ack)} tasks")
        elif args.command == "normalize":
            print(f"Normalized {normalize_all(conn)} raw rows")
        elif args.command == "dedupe":
            print(f"Linked {dedupe_all(conn)} normalized rows")
        elif args.command == "coverage":
            print(json.dumps(coverage_report(conn, args.location, args.category), indent=2))
        elif args.command == "export":
            print(f"Exported {export_businesses(conn, args.location, args.category, args.format, args.out)}")


if __name__ == "__main__":
    main()
