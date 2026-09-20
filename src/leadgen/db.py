from __future__ import annotations

import sqlite3
from pathlib import Path

from .settings import DB_PATH


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categories (
  id TEXT PRIMARY KEY,
  canonical_name TEXT NOT NULL,
  tier INTEGER NOT NULL,
  variants TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  default_depth INTEGER NOT NULL DEFAULT 1,
  grid_profile TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS locations (
  id TEXT PRIMARY KEY,
  country TEXT NOT NULL,
  region TEXT,
  city TEXT NOT NULL,
  bbox_min_lat REAL NOT NULL,
  bbox_min_lng REAL NOT NULL,
  bbox_max_lat REAL NOT NULL,
  bbox_max_lng REAL NOT NULL,
  grid_profile TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grid_cells (
  id TEXT PRIMARY KEY,
  location_id TEXT NOT NULL REFERENCES locations(id),
  center_lat REAL NOT NULL,
  center_lng REAL NOT NULL,
  bbox_min_lat REAL NOT NULL,
  bbox_min_lng REAL NOT NULL,
  bbox_max_lat REAL NOT NULL,
  bbox_max_lng REAL NOT NULL,
  grid_cell_km REAL NOT NULL,
  radius_meters INTEGER NOT NULL,
  zoom INTEGER NOT NULL,
  density_profile TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scrape_tasks (
  id TEXT PRIMARY KEY,
  category_id TEXT NOT NULL REFERENCES categories(id),
  location_id TEXT NOT NULL REFERENCES locations(id),
  grid_cell_id TEXT NOT NULL REFERENCES grid_cells(id),
  keyword TEXT NOT NULL,
  scraper_provider TEXT NOT NULL DEFAULT 'gosom_google_maps_scraper',
  depth INTEGER NOT NULL,
  zoom INTEGER NOT NULL,
  radius_meters INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  attempt_count INTEGER NOT NULL DEFAULT 0,
  priority INTEGER NOT NULL DEFAULT 100,
  started_at TEXT,
  completed_at TEXT,
  error_message TEXT,
  raw_output_path TEXT,
  result_count INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(category_id, location_id, grid_cell_id, keyword)
);

CREATE TABLE IF NOT EXISTS raw_scrape_results (
  id TEXT PRIMARY KEY,
  scrape_task_id TEXT NOT NULL REFERENCES scrape_tasks(id),
  provider TEXT NOT NULL,
  raw_json TEXT NOT NULL,
  raw_hash TEXT NOT NULL,
  extracted_place_id TEXT,
  extracted_cid TEXT,
  extracted_data_id TEXT,
  extracted_title TEXT,
  extracted_phone TEXT,
  extracted_website TEXT,
  extracted_latitude REAL,
  extracted_longitude REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(raw_hash)
);

CREATE TABLE IF NOT EXISTS normalized_businesses (
  id TEXT PRIMARY KEY,
  raw_result_id TEXT NOT NULL REFERENCES raw_scrape_results(id),
  title TEXT,
  category TEXT,
  address TEXT,
  city TEXT,
  region TEXT,
  country TEXT,
  postal_code TEXT,
  phone TEXT,
  website TEXT,
  website_domain TEXT,
  google_maps_link TEXT,
  place_id TEXT,
  cid TEXT,
  data_id TEXT,
  latitude REAL,
  longitude REAL,
  review_count INTEGER,
  review_rating REAL,
  status TEXT,
  open_hours TEXT,
  emails TEXT,
  source_category_id TEXT,
  source_keyword TEXT,
  source_location_id TEXT,
  source_grid_cell_id TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_identities (
  id TEXT PRIMARY KEY,
  canonical_title TEXT,
  canonical_phone TEXT,
  canonical_website_domain TEXT,
  canonical_address TEXT,
  canonical_city TEXT,
  canonical_region TEXT,
  canonical_country TEXT,
  canonical_latitude REAL,
  canonical_longitude REAL,
  best_place_id TEXT,
  best_cid TEXT,
  best_google_maps_link TEXT,
  categories TEXT NOT NULL DEFAULT '[]',
  source_count INTEGER NOT NULL DEFAULT 0,
  first_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS business_sources (
  id TEXT PRIMARY KEY,
  business_identity_id TEXT NOT NULL REFERENCES business_identities(id),
  normalized_business_id TEXT NOT NULL REFERENCES normalized_businesses(id),
  match_method TEXT NOT NULL,
  match_confidence REAL NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(business_identity_id, normalized_business_id)
);

CREATE TABLE IF NOT EXISTS export_runs (
  id TEXT PRIMARY KEY,
  export_type TEXT NOT NULL,
  filters TEXT NOT NULL,
  row_count INTEGER NOT NULL,
  file_path TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_raw_place_id ON raw_scrape_results(extracted_place_id);
CREATE INDEX IF NOT EXISTS idx_raw_cid ON raw_scrape_results(extracted_cid);
CREATE INDEX IF NOT EXISTS idx_norm_place_id ON normalized_businesses(place_id);
CREATE INDEX IF NOT EXISTS idx_norm_cid ON normalized_businesses(cid);
CREATE INDEX IF NOT EXISTS idx_norm_phone ON normalized_businesses(phone);
CREATE INDEX IF NOT EXISTS idx_norm_website_domain ON normalized_businesses(website_domain);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON scrape_tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_location_category ON scrape_tasks(location_id, category_id);
"""


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path = DB_PATH) -> None:
    with connect(path) as conn:
        conn.executescript(SCHEMA)
