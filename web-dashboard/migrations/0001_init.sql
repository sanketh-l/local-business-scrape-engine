CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  city TEXT NOT NULL,
  country TEXT NOT NULL,
  area TEXT,
  category TEXT NOT NULL,
  coverage TEXT NOT NULL,
  max_areas INTEGER NOT NULL,
  worker_limit INTEGER NOT NULL,
  real_scrape INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'created',
  run_id INTEGER,
  run_url TEXT,
  areas_total INTEGER NOT NULL DEFAULT 0,
  areas_completed INTEGER NOT NULL DEFAULT 0,
  squares_total INTEGER NOT NULL DEFAULT 0,
  squares_completed INTEGER NOT NULL DEFAULT 0,
  raw_rows INTEGER NOT NULL DEFAULT 0,
  unique_businesses INTEGER NOT NULL DEFAULT 0,
  message TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS job_areas (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  area_name TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'queued',
  squares_total INTEGER NOT NULL DEFAULT 0,
  squares_completed INTEGER NOT NULL DEFAULT 0,
  raw_rows INTEGER NOT NULL DEFAULT 0,
  unique_businesses INTEGER NOT NULL DEFAULT 0,
  position INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(id),
  business_name TEXT,
  primary_category TEXT,
  phone TEXT,
  has_website TEXT,
  website TEXT,
  google_maps_link TEXT,
  address TEXT,
  city TEXT,
  region TEXT,
  country TEXT,
  latitude REAL,
  longitude REAL,
  rating REAL,
  review_count INTEGER,
  status TEXT,
  place_id TEXT,
  cid TEXT,
  source_keywords TEXT,
  source_grid_cells_count INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_job_areas_job_id ON job_areas(job_id);
CREATE INDEX IF NOT EXISTS idx_leads_job_id ON leads(job_id);
