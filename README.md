# Local Business Scrape Engine

MVP pipeline for config-driven local-business discovery using micro-grid Google Maps searches.

## Legal And Compliance Warning

Google Maps Platform Terms include restrictions against scraping and exporting Google Maps content. This project does not make usage legally safe. Before running scraping jobs, review Google terms and all relevant privacy, marketing, and data-protection laws including GDPR, CCPA, CAN-SPAM, PECR, CASL, TRAI, and local equivalents.

This MVP includes a compliance gate option: set `LEADGEN_REQUIRE_COMPLIANCE_ACK=true` and workers will require `--compliance-ack`.

## What This Builds

- Category and location config loading.
- Micro-grid generation from a city bounding box.
- Scrape task generation by `category x keyword x grid_cell`.
- Worker command generation for `gosom/google-maps-scraper`.
- Raw JSON result ingestion.
- Normalized business rows.
- Deduped business identities.
- Coverage reporting.
- CSV/XLSX export.

SQLite is used for the local MVP so you can validate the flow quickly. The schema mirrors the planned PostgreSQL tables closely enough for later migration.

## Setup

```powershell
cd C:\Users\sanke\OneDrive\Desktop\local-business-scrape-engine
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Install the upstream scraper separately if you want to run real scrape jobs:

```powershell
# Example only; follow upstream docs for your OS/container setup.
# https://github.com/gosom/google-maps-scraper
```

## MVP Flow

```powershell
leadgen init-db
leadgen load-config --categories configs/categories.yaml --locations configs/locations.yaml
leadgen generate-grid --location austin_tx
leadgen generate-tasks --location austin_tx --category plumber
leadgen worker --limit 1 --dry-run
```

The dry run prints the exact `google-maps-scraper` command without scraping.

After real worker runs:

```powershell
leadgen normalize
leadgen dedupe
leadgen coverage --location austin_tx --category plumber
leadgen export --location austin_tx --category plumber --format xlsx --out data/exports/austin-plumbers.xlsx
```

## Dashboard

The easiest way to use this is the dashboard.

Run locally:

```powershell
cd C:\Users\sanke\OneDrive\Desktop\local-business-scrape-engine
pip install -e .
streamlit run src/leadgen/dashboard.py
```

Or run the included PowerShell launcher:

```powershell
cd C:\Users\sanke\OneDrive\Desktop\local-business-scrape-engine
.\scripts\run_dashboard.ps1
```

Then open the browser URL Streamlit prints, usually:

```text
http://localhost:8501
```

Dashboard flow:

1. Enter a city, for example `Bengaluru`.
2. Enter a country, for example `India`.
3. To target one area only, switch `Target scope` to `Specific area/neighborhood` and enter something like `Nandini Layout`.
4. Enter a business keyword, for example `plumber` or `electrician`.
5. Keep `Dry run only` enabled for the first run.
6. Click `1. Find City Bounds`.
7. Review estimated city/area size, grid squares, and task count.
8. Click `2. Generate Squares And Queue`.
9. Click `3. Run Worker Batch` with `Worker limit per run = 1` first.
10. For real scraping, disable `Dry run only`, check the compliance box, and start with a small worker limit.
11. After results exist, click `4. Normalize And Dedupe`.
12. Click `5. Export File` and download CSV/XLSX.

What it does automatically:

- Geocodes the city to a bounding box.
- Estimates the city size.
- Chooses grid cell size based on coverage intensity.
- Splits the city into overlapping micro-squares.
- Generates one task for every keyword variant in every square.
- Runs those tasks one batch at a time.
- Stores raw data, dedupes results, and exports Excel-compatible files.

Important: this is designed to approximate street-level coverage by searching many small coordinate cells. It can find far more listings than one broad city search, but no system can honestly guarantee that it will find every single business or every single street.

## Scaling Notes

Start with one city and one category. Do not run every category/country at once. Increase throughput only after measuring failure rate, zero-result rate, duplicate rate, and unique businesses per second.

For larger production use, replace the local SQLite execution model with PostgreSQL plus Redis/Celery or another durable queue, long-running scraper workers, proxy pools, and adaptive throttling.

## Docker Usage

Build the container:

```powershell
docker build -t leadgen .
```

Run the same MVP commands in Docker:

```powershell
docker run --rm -v ${PWD}\data:/app/data leadgen init-db
docker run --rm -v ${PWD}\data:/app/data leadgen load-config --categories configs/categories.yaml --locations configs/locations.yaml
docker run --rm -v ${PWD}\data:/app/data leadgen generate-grid --location austin_tx
docker run --rm -v ${PWD}\data:/app/data leadgen generate-tasks --location austin_tx --category plumber
docker run --rm -v ${PWD}\data:/app/data leadgen worker --limit 1 --dry-run
```

Docker Compose quick check:

```powershell
docker compose build
docker compose run --rm leadgen init-db
```

## GitHub Actions Cloud Usage

This repo includes two workflows:

- `.github/workflows/tests.yml`: runs tests and validates the MVP commands on every push or manual run.
- `.github/workflows/manual-pipeline.yml`: lets you manually run a small pipeline from the GitHub Actions UI.

To use it:

1. Create a new GitHub repository.
2. Push this folder to GitHub.
3. Open the repo on GitHub.
4. Go to `Actions`.
5. Run `Tests` first.
6. Run `Manual Leadgen Pipeline`.
7. Keep `dry_run` as `true` first.
8. Download the `leadgen-output...` artifact from the workflow run.

If using GitHub CLI from this folder:

```powershell
git init
git add .
git commit -m "Initial leadgen cloud pipeline"
gh repo create local-business-scrape-engine --private --source . --remote origin --push
```

Run the form-like workflow from the browser:

1. Open your GitHub repo.
2. Click `Actions`.
3. Click `Manual Leadgen Pipeline`.
4. Click `Run workflow`.
5. Fill in the fields like a form.
6. Start with `dry_run=true` and `limit=1`.

There is also an issue form at `Issues -> New issue -> Scrape Request`. This is the easiest non-localhost dashboard: submit the form and GitHub Actions starts automatically.

Issue form behavior:

- Leave `Area/neighborhood optional` blank to run the full city.
- The workflow discovers city areas/neighborhoods from OpenStreetMap/Overpass.
- It saves an `areas-...csv` showing the discovered areas.
- It generates grid-square scrape tasks for the discovered areas.
- Dry-run mode creates the queue and prints commands but does not create leads.
- Real scrape mode requires `I_ACCEPT_LEGAL_RISK`.
- The workflow comments back on the issue with counts and artifact details.

If the CSV is blank, it means no real scraped rows exist yet. Dry-run mode cannot produce business leads.

The manual workflow inputs are:

- `location`: default `austin_tx`.
- `category`: default `plumber`.
- `limit`: number of worker tasks to run.
- `dry_run`: `true` prints scraper commands only.
- `compliance_ack`: must be `I_ACCEPT_LEGAL_RISK` for non-dry-run execution.

Important limitations:

- GitHub Actions is suitable for tests, dry runs, and very small manual jobs.
- GitHub Actions is not the right place for sustained high-throughput scraping.
- Real scraping in Actions uses the `gosom/google-maps-scraper` Docker image through `scripts/google-maps-scraper-docker.sh`.
- For serious cloud execution, use a VPS/cloud VM or container service with PostgreSQL, Redis/Celery, long-running workers, proxy configuration, and monitoring.
