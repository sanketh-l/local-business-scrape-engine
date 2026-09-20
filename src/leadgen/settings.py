from __future__ import annotations

import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def project_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


DB_PATH = project_path(os.getenv("LEADGEN_DB_PATH", "data/leadgen.sqlite"))
RAW_DIR = project_path(os.getenv("LEADGEN_RAW_DIR", "data/raw"))
EXPORT_DIR = project_path(os.getenv("LEADGEN_EXPORT_DIR", "data/exports"))
SCRAPER_BIN = os.getenv("LEADGEN_SCRAPER_BIN", "google-maps-scraper")
REQUIRE_COMPLIANCE_ACK = os.getenv("LEADGEN_REQUIRE_COMPLIANCE_ACK", "false").lower() == "true"
