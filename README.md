# Enterprise Web Scraping Pipeline – Books Data Engineering System

## Project Overview

A Scrapy application that crawls [books.toscrape.com](https://books.toscrape.com/index.html).
It discovers every book category dynamically, randomly selects 5-10 of them, walks all
listing pages of each, randomly picks **exactly 5 books per category** and extracts the
book details. Items are cleaned and validated in item pipelines, stored in SQLite and
exported to JSON, CSV and XML. The project is containerised with Docker and deployable
with Scrapyd.

## Features

- Dynamic category discovery - no hardcoded category names or URLs
- Eligibility check: only categories that really contain 5+ books can be selected
  (see [Design Decisions](#design-decisions))
- Random 5-10 categories, exactly 5 random books each; pagination handled
- Item pipelines: clean -> validate -> deduplicate -> store
- Feed exports (JSON / CSV / XML) configured in `settings.py`; SQLite via a pipeline;
  all four outputs contain identical data
- Logging for crawling, processing and errors; docstrings enforced by `ruff`
- User-Agent rotation downloader middleware
- Dockerfile + Scrapyd, with the project auto-deployed when the container starts

## Tech Stack

| Area | Tool |
| --- | --- |
| Language | Python 3.14 |
| Web scraping | Scrapy 2.19 |
| Database | SQLite |
| Data processing | Scrapy Item Pipelines |
| Feed exports | JSON, CSV, XML |
| Deployment | Scrapyd, scrapyd-client |
| Dependency management | [uv](https://docs.astral.sh/uv/) (`pyproject.toml` + `uv.lock`) |
| Testing | pytest |
| Code quality | Ruff, pre-commit |
| Containerisation | Docker, Docker Compose |

## Installation Guide

### Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Git

### 1. Clone the repository

```bash
git clone https://github.com/frost23z/books-to-scrape-scrapy
cd books-to-scrape-scrapy
```

### 2. Install dependencies (local development)

```bash
uv sync
```

`uv` reads `.python-version`, installs Python 3.14 if necessary, and creates a virtual
environment with the locked project dependencies and development tools.

### 3. Run the spider locally

```bash
uv run scrapy crawl books
```

### 4. Run tests and linting

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

### 5. Run with Docker Compose

Build the image and start Scrapyd in the background:

```bash
docker compose up --build -d
```

Check the container status:

```bash
docker compose ps
docker compose logs -f scrapyd
```

Once Scrapyd is ready, the entrypoint automatically deploys the project. The Scrapyd
interface is available at [http://localhost:6800](http://localhost:6800).

To stop the service:

```bash
docker compose down
```

The `output/` directory on the host stores the exported feeds and the SQLite database
when running through Docker Compose.

## Environment Setup

No `.env` file is needed. Every setting has a default and can be overridden with
environment variables. The Docker Compose file defines the container's variables
directly.

| Variable | Default | Purpose |
| --- | --- | --- |
| `OUTPUT_DIR` | `output` locally; `/app/output` in Docker | Directory for the JSON, CSV and XML feed exports |
| `DATABASE_PATH` | `data/books.db` locally; `/app/output/books.db` with Docker Compose | Path to the SQLite database |
| `DATABASE_RESET_ON_START` | `1` | Clears the books table at the start of a crawl so the database matches that run's feeds |
| `DOWNLOAD_DELAY` | `1` | Delay in seconds between requests |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `HOST_UID` / `HOST_GID` | `1000` / `1000` | Docker Compose only: user and group the container runs as |

Docker Compose overrides `OUTPUT_DIR` and `DATABASE_PATH` to use `/app/output`, which is
mounted to `./output` on the host. Both the feed files and the database therefore persist
outside the container. (The Dockerfile's own default for `DATABASE_PATH` is
`/app/data/books.db`; it is only used if you run the image without overriding it and
without mounting `/app/data`.)

> **Important:** with `DATABASE_RESET_ON_START=1`, starting a new crawl clears the
> existing `books` table before storing the new results. Set it to `0` to retain existing
> rows and use the repository's upsert behaviour across runs.

## Running the Spider

```bash
uv run scrapy crawl books
```

Optional spider arguments:

```bash
uv run scrapy crawl books \
  -a min_categories=5 -a max_categories=10 -a books_per_category=5 -a seed=42
```

| Argument | Meaning |
| --- | --- |
| `min_categories` | Minimum number of categories to sample (default 5) |
| `max_categories` | Maximum number of categories to sample (default 10) |
| `books_per_category` | Books extracted per category (default 5) |
| `seed` | Makes the random selection reproducible |

A full run takes a few minutes because the crawl is deliberately polite (1 request at a
time, 1 s delay, `robots.txt` obeyed).

Tests and linting:

```bash
uv run pytest            # unit tests + end-to-end crawl of an offline mock site
uv run ruff check . && uv run ruff format --check .
```

## Docker Setup Guide

The project uses Docker to run Scrapyd as a service and to deploy the Scrapy project
automatically when the container starts.

### Build and start (recommended: Docker Compose)

```bash
docker compose up --build -d
```

This builds the image, creates the `books-scrapyd` container, publishes port `6800`, and
mounts the host's `output/` directory at `/app/output`.

### Verify the container

```bash
docker compose ps
docker compose logs -f scrapyd
curl http://localhost:6800/daemonstatus.json
```

The Dockerfile defines a health check against Scrapyd's daemon status endpoint. Wait for
the container to report `healthy` before scheduling a crawl.

### Run without Docker Compose

```bash
docker build -t books-scrapyd .
mkdir -p output

docker run -d \
  --name books-scrapyd \
  --user "$(id -u):$(id -g)" \
  -p 6800:6800 \
  -e OUTPUT_DIR=/app/output \
  -e DATABASE_PATH=/app/output/books.db \
  -e DATABASE_RESET_ON_START=1 \
  -e LOG_LEVEL=INFO \
  -v "$(pwd)/output:/app/output" \
  books-scrapyd
```

This runs the container with the current host user's UID and GID, which avoids
root-owned output files on Linux. The mounted directory must be writable by that user.

### Stop and remove the container

With Docker Compose:

```bash
docker compose down
```

For a container started directly with `docker run`:

```bash
docker stop books-scrapyd
docker rm books-scrapyd
```

Removing the container does not remove the host's `output/` directory.

### Configuration Reference

#### Dockerfile

The image is based on `python:3.14-slim` and uses `uv` to install the locked production
dependencies. It also:

- Copies the `uv` binary from the official `ghcr.io/astral-sh/uv` image.
- Sets `PYTHONUNBUFFERED=1` and `PYTHONDONTWRITEBYTECODE=1`.
- Installs `curl` for the health check and the startup readiness check.
- Uses `/opt/venv` as the Python virtual environment (`UV_PROJECT_ENVIRONMENT`) and puts
  it first on `PATH`.
- Installs dependencies from `pyproject.toml`, `uv.lock` and `.python-version` before
  copying the source, so the dependency layer is cached between code changes.
- Excludes development dependencies with `uv sync --frozen --no-dev`.
- Copies `scrapyd.conf` to `/etc/scrapyd/scrapyd.conf`.
- Exposes port `6800` and defines a `HEALTHCHECK` (every 15 s, 3 s timeout, 5 retries).
- Starts `docker-entrypoint.sh`, which deploys the project automatically.

#### Entrypoint (`docker-entrypoint.sh`)

1. Starts Scrapyd in the background.
2. Waits (up to 30 attempts, 1 s apart) for `http://localhost:6800/daemonstatus.json`
   to respond; exits with an error if Scrapyd never becomes ready.
3. Runs `scrapyd-deploy` to deploy the project.
4. Keeps Scrapyd in the foreground so the container stays alive, and stops it cleanly on
   `SIGINT` / `SIGTERM`.

#### Docker Compose

| Setting | Value | Purpose |
| --- | --- | --- |
| Service name | `scrapyd` | Compose service identifier |
| Container name | `books-scrapyd` | Explicit container name |
| Port mapping | `6800:6800` | Makes the Scrapyd API available on the host |
| User | `${HOST_UID:-1000}:${HOST_GID:-1000}` | UID and GID of the container process |
| Volume | `./output:/app/output` | Persists feed exports and the SQLite database |
| `OUTPUT_DIR` | `/app/output` | Feed export directory |
| `DATABASE_PATH` | `/app/output/books.db` | Stores SQLite alongside the feed files |
| `DATABASE_RESET_ON_START` | `1` | Clears the books table at the start of a crawl |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

On Linux, set `HOST_UID` and `HOST_GID` so that files written to `./output` belong to
your user:

```bash
export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"
docker compose up --build -d
```

Make sure the host's `output/` directory exists and is writable by the configured
container user.

## Scrapyd Deployment Guide

### In Docker

The entrypoint deploys the project automatically; no separate deployment command is
required. Verify and run:

```bash
curl http://localhost:6800/listprojects.json
curl "http://localhost:6800/listspiders.json?project=books_scraper"
curl http://localhost:6800/schedule.json -d project=books_scraper -d spider=books
curl "http://localhost:6800/listjobs.json?project=books_scraper"
```

Pass spider arguments with `-d` and Scrapy settings with `-d setting=...`:

```bash
curl http://localhost:6800/schedule.json \
  -d project=books_scraper \
  -d spider=books \
  -d seed=42 \
  -d setting=DOWNLOAD_DELAY=0
```

Job logs are available at:

```text
http://localhost:6800/logs/books_scraper/books/<jobid>.log
```

The Scrapyd web UI is at <http://localhost:6800>.

When a job finishes (a few minutes with the default 1 s delay), the results are in the
host's `output/` folder: `books.json`, `books.csv`, `books.xml` and `books.db`. Check the
job state with `listjobs.json` (it moves from `running` to `finished`).

### Without Docker

Open two terminals in the project directory (the folder containing `scrapy.cfg`).

Terminal 1 (keep it running):

```bash
uv run scrapyd
```

Terminal 2:

```bash
uv run scrapyd-deploy
```

Then use the same `curl` commands as above. `scrapy.cfg` already contains
`url = http://localhost:6800/`. Re-run `scrapyd-deploy` after changing code.

Without Docker, relative paths resolve against Scrapyd's working directory, so export
absolute `OUTPUT_DIR` and `DATABASE_PATH` values first.

## Output Format Description

| Field | Type | Notes |
| --- | --- | --- |
| `title` | string | whitespace-normalised |
| `price` | float | currency symbol removed (`£51.77` -> `51.77`) |
| `availability` | bool | text starting with "In stock" (any count suffix) -> `true`, else `false` |
| `product_url` | string | absolute product URL (unique key) |
| `image_url` | string | absolute image URL |
| `category` | string | name of the category the book was sampled from |

Files (overwritten on each run): `output/books.json` (array), `output/books.csv`,
`output/books.xml` (`<books><book>...</book></books>`). They are configured through
`FEEDS` in `books_scraper/settings.py`.

## Database Configuration

SQLite, file `data/books.db` locally (`DATABASE_PATH`; `output/books.db` with Docker
Compose), table `books`:

| Column | Type |
| --- | --- |
| `product_url` | TEXT PRIMARY KEY |
| `title` | TEXT NOT NULL |
| `price` | REAL NOT NULL |
| `availability` | INTEGER NOT NULL (0/1) |
| `image_url` | TEXT |
| `category` | TEXT NOT NULL |

Rows are written by `SQLitePipeline` (upsert on `product_url`) from the same cleaned
items that the feed exporters receive. Inspect with:

```bash
sqlite3 data/books.db "SELECT category, COUNT(*) FROM books GROUP BY 1;"
```

To use MongoDB, implement `BookRepository` (`storage/repository.py`) and inject it into
the pipeline - the pipeline code does not change.

## Architecture Diagram

```text
scrapy crawl books  (or Scrapyd schedule.json)
   |
   v
BooksSpider
   |  1. homepage ----------> CategoryParser        discover ALL categories
   |  2. page 1 of each ----> ListingParser         probe: does it hold >= 5 books?
   |  3. RandomSelector ----> 5-10 eligible categories
   |     remaining pages ---> ListingParser         collect every book URL
   |  4. RandomSelector ----> exactly 5 books per category
   |     product pages -----> ProductParser ------> BookItem (raw)
   v
Item pipelines (lower number runs first)
   CleaningPipeline(100) -> ValidationPipeline(200) -> DuplicatesPipeline(300)
        -> SQLitePipeline(400) -> BookRepository -> books.db
   v
Feed exports (settings.FEEDS) -> output/books.json, books.csv, books.xml
```

## Folder Structure

```text
.
├── books_scraper/
│   ├── items.py            BookItem (data contract)
│   ├── middlewares.py      RandomUserAgentMiddleware
│   ├── pipelines.py        Cleaning, Validation, Duplicates, SQLite pipelines
│   ├── settings.py         settings, pipelines, FEEDS, politeness
│   ├── spiders/books.py    BooksSpider (orchestration only)
│   ├── services/           parsers.py, selection.py, cleaning.py
│   └── storage/repository.py   BookRepository + SQLite implementation
├── tests/                  unit tests, end-to-end test, mock_site/ generator
├── scrapy.cfg              project + Scrapyd deploy target
├── scrapyd.conf            Scrapyd server configuration (used in Docker)
├── Dockerfile  docker-compose.yml  docker-entrypoint.sh  .dockerignore
├── pyproject.toml  uv.lock  .python-version
├── output/  data/          feeds and database (git-ignored contents)
└── README.md
```

## Design Decisions

- **SRP / DRY**: parsing, random selection, cleaning and storage live in separate small
  classes/functions; the spider only orchestrates. Cleaning exists once and is used by
  the pipeline for every output.
- **Open/closed + dependency inversion**: the pipeline depends on the `BookRepository`
  interface, so another database needs no pipeline changes. Parsers, selection and the
  repository are small, injectable and unit-testable without a network.
- **Eligibility probe.** Many categories on the site contain fewer than 5 books
  (1-3 is common). If categories were chosen first, "exactly 5 books per category" would
  be impossible for those. The spider therefore fetches page 1 of every category (one
  cheap request each; the page is reused, not fetched twice), keeps categories with 5+
  books, then picks 5-10 of them at random.
- **Pipelines do all cleaning**, and feed exports run after pipelines, so JSON, CSV, XML
  and SQLite always contain the same data. The feeds overwrite and the table resets at
  the start of each run, so all outputs describe the same run.
- **`items_dir` is empty in `scrapyd.conf`.** If set, Scrapyd injects its own `FEEDS`
  setting and would replace the JSON/CSV/XML feeds configured in `settings.py`.
- **`max_proc = 1`** because concurrent jobs would share one SQLite file and one set of
  output files.
- **Reproducibility**: eligible categories are sorted before sampling, so the same
  `seed` always gives the same selection regardless of response arrival order.
- **Scrapy 2.19 signatures**: pipeline/middleware methods omit the deprecated `spider`
  argument.
- **Docker runs as a non-root user** (`HOST_UID` / `HOST_GID`) and keeps the database in
  the mounted `output/` directory, so all results persist on the host and are owned by
  the host user.

## Known Limitations

- SQLite only; MongoDB is possible via `BookRepository` but not implemented.
- Selectors target the current books.toscrape.com layout; if the markup changes, only
  the parser classes need updating.
- If a book request fails after retries, that category ends up with fewer than 5 books
  (the failure is logged as an error).
- Run one job at a time (shared output files and database).
- If `HOST_UID` / `HOST_GID` do not match the owner of `./output`, the container may not
  be able to write there (or files may be owned by a different user).
- The end-to-end tests use an offline mock of the site; the full pipeline was not run
  against the live site in the development environment.
