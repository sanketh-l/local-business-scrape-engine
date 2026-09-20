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

There is also an issue form at `Issues -> New issue -> Scrape Request`. Use that to collect/plan scrape requests before running them.

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
