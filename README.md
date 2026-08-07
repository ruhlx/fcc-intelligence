# FCC Regulatory Contact Intelligence Platform

Extracts regulatory and certification contacts (Certification Managers, Product
Compliance, Regulatory Affairs, Product Security) from **FCC Equipment
Authorization** filings and builds a searchable, priority-scored database for
B2B outbound sales.

## What it does

```
Company name ──► FCC EAS search ──► FCC IDs / filings ──► exhibit PDFs
      │                                                        │
      ▼                                                        ▼
  companies                                            text extraction
  filings                                          (pdfplumber→PyMuPDF→OCR)
                                                             │
                                                             ▼
                                              OpenAI Responses API extraction
                                                             │
                            classify ─► filter ─► deduplicate ─► priority score
                                                             │
                                                             ▼
                                          Postgres ──► REST API ──► contacts.csv
```

## Tech stack

Python 3.12 · Poetry · PostgreSQL · SQLAlchemy 2.0 · Alembic · Pydantic v2 ·
FastAPI · httpx · BeautifulSoup4 · pdfplumber · pypdf · PyMuPDF · OpenAI
Responses API · Docker · pytest · Ruff · mypy.

## Project layout

```
app/
  api/          FastAPI routers + dependencies (Stage 7)
  crawler/      FCC EAS client, company lookup (Stage 1), doc locator (Stage 2), adapters
  parser/       PDF text extraction pipeline + cleaning (Stage 3)
  extractor/    OpenAI Responses API structured extraction (Stage 4)
  enrichment/   classification (Stage 5), dedup (Stage 6), priority (Stage 9)
  models/       SQLAlchemy 2.0 ORM models + enums
  db/           engine/session + repositories
  services/     pipeline orchestration, ingestion, CSV export (Stage 8)
  prompts/      LLM prompt templates
frontend/       React + TypeScript + Vite SPA (contacts dashboard)
scripts/        run_pipeline.py, export_csv.py
alembic/        migrations
docker/         Dockerfile (backend)
tests/          pytest suite
```

## Run everything locally (one process, no cloud)

The whole app can run on your machine against a local **SQLite** file, with the
API also serving the built frontend — so a single `uvicorn` is the entire app.

```bash
poetry install && poetry run playwright install firefox
cp .env.example .env          # defaults to sqlite:///./fcc.db, AUTO_MIGRATE=true
poetry run alembic upgrade head           # create the local schema
(cd frontend && npm install && npm run build)   # build the SPA (same-origin)
```

Collect contacts, then browse them:

```bash
# Default = structured 731 "Responsible Party" only — fast, no LLM/quota:
poetry run python -m scripts.run_pipeline u-blox

# Then serve the API + UI together at http://localhost:8000
poetry run uvicorn app.main:app
```

Deep mode (also download and LLM-mine exhibit PDFs — needs an LLM key/quota):

```bash
poetry run python -m scripts.run_pipeline --pdfs u-blox
```

### Two extraction modes

| Mode | How | Source | LLM |
| ---- | --- | ------ | --- |
| **Default** | `run_pipeline <company>` | 731 form Responsible Party (name/title/email/phone), parsed structurally | none |
| **Deep** | `run_pipeline --pdfs <company>` or `EXTRACT_PDFS=true` | above **+** exhibit PDFs (cover letters, attestations…) | yes |

The default mode is unaffected by LLM rate limits; deep mode is bounded by your
provider's quota (e.g. Gemini's free tier is ~20 requests/day).

## Discovery mode: find contacts without naming a company

FCC has no "search by job title" or "search by country" field — but it does
allow a **blank-applicant search over a grant-date window**, which returns
filings from *every* company that got an authorization in that window. Discovery
mode uses that to find new companies/contacts automatically, then keeps only
the region you want (client-side, using the country each filing already
reports) and reads each match's 731 Responsible Party — same free, no-LLM path
as default mode.

```bash
# Last 3 days, Europe only (the defaults) — no company name needed:
poetry run python -m scripts.discover_filings

# Wider window, worldwide:
poetry run python -m scripts.discover_filings --days 7 --regions all

# Restrict to specific countries:
poetry run python -m scripts.discover_filings --regions "Germany,France,Sweden"
```

The same control is in the UI (**"Or discover automatically"**, below the
company search) and the API (`POST /discover { "days": 3, "regions": "europe" }`).

**Run it automatically in the background:** set `AUTO_DISCOVER_INTERVAL_HOURS`
in `.env` (e.g. `6`) and it runs on that interval for as long as
`uvicorn app.main:app` stays up — no cron needed, no manual clicks. This is an
in-process scheduler, not OS-level cron: the schedule resets if the server
restarts, and it only runs while the process is alive.

The Europe country list lives in [`app/crawler/regions.py`](app/crawler/regions.py)
— edit `EUROPE_COUNTRIES` to adjust it.

## One-click deploy (Render)

The repo ships a [`render.yaml`](render.yaml) Blueprint that provisions the whole
stack — managed Postgres, the FastAPI API, and the static frontend. The API runs
`alembic upgrade head` **on startup** (via `AUTO_MIGRATE=true`), so no paid
pre-deploy step is required — it works entirely on Render's free tier.

1. In Render: **New → Blueprint** and select this repo.
2. When prompted, provide the secrets marked `sync: false`: your `GEMINI_API_KEY`
   (or `OPENAI_API_KEY`), and set the frontend's `VITE_API_BASE_URL` to the API
   service URL (e.g. `https://fcc-api.onrender.com`).
3. Open the frontend URL, type a company name, paste your LLM key, and click
   **Run** — no CLI or shell needed.

> Note: `DATABASE_URL` is normalised automatically, so Render's `postgres://`
> connection string works verbatim (it's rewritten to `postgresql+psycopg://`).

## Run the pipeline from the UI/API (no CLI)

Ingestion can be triggered over HTTP, so the SPA drives it end to end:

```
POST /ingest        { "company": "u-blox", "provider": "gemini", "api_key": "…" }
                    → 202 { "id": "…", "status": "pending" }
GET  /ingest/{id}   → { "status": "completed", "report": { … } }
```

Jobs run in the background; the UI polls `/ingest/{id}` and refreshes the table
when done. `api_key`/`provider` are optional per-request overrides — omit them to
use the server's env config. Set `INGEST_TOKEN` to require an `X-Ingest-Token`
header on `/ingest`.

## Quick start (Docker)

```bash
cp .env.example .env          # add your OPENAI_API_KEY
docker compose up --build     # starts Postgres, runs migrations, serves the API
```

Then open:
- **Web UI (SPA):** http://localhost:8080
- **API docs (Swagger):** http://localhost:8000/docs

Run the pipeline and export inside the running `api` container:

```bash
docker compose exec api python -m scripts.run_pipeline u-blox
docker compose exec api python -m scripts.export_csv --out /data/contacts.csv
```

## Local development

```bash
poetry install
cp .env.example .env
# start a local Postgres (or `docker compose up db`), then:
poetry run alembic upgrade head
poetry run uvicorn app.main:app --reload
```

Run the ingestion pipeline for one or more applicants:

```bash
poetry run python -m scripts.run_pipeline u-blox "Nordic Semiconductor"
```

## Frontend (React + TypeScript SPA)

A single-page dashboard in [`frontend/`](frontend) to search, filter and
priority-rank contacts and export CSV. It talks to the REST API over CORS.

```bash
cd frontend
npm install
cp .env.example .env          # set VITE_API_BASE_URL (default http://localhost:8000)
npm run dev                   # dev server at http://localhost:5173
# or: npm run build && npm run preview   # production build at http://localhost:4173
```

Make sure the SPA's origin is present in the backend `CORS_ORIGINS` (the
defaults already include ports 5173/4173/8080). Under Docker the `web` service
builds and serves the SPA via nginx at http://localhost:8080.

Features: debounced free-text search (`/search`), title/country/company filters
(`/contacts`), colour-coded category badges, 0–100 priority meters, per-contact
FCC-ID counts, and a one-click CSV export. Styled for both light and dark mode.

## Configuration (Stage 10)

All settings come from the environment / `.env` (see `.env.example`):

| Variable          | Purpose                                             |
| ----------------- | --------------------------------------------------- |
| `LLM_PROVIDER`    | Extraction backend: `openai` or `gemini`            |
| `OPENAI_API_KEY`  | OpenAI key (when `LLM_PROVIDER=openai`)             |
| `OPENAI_MODEL`    | OpenAI model id (default `gpt-4o-2024-08-06`)       |
| `GEMINI_API_KEY`  | Google Gemini key (when `LLM_PROVIDER=gemini`)      |
| `GEMINI_MODEL`    | Gemini model id (default `gemini-2.5-flash`)        |
| `DATABASE_URL`    | SQLAlchemy Postgres URL                             |
| `DATA_DIRECTORY`  | Where downloaded PDFs are stored                    |
| `LOG_LEVEL`       | `INFO`, `DEBUG`, …                                  |
| `LOG_FORMAT`      | `console` (dev) or `json` (prod)                   |

### Choosing the LLM provider (Stage 4)

Extraction runs behind a `ContactExtractor` protocol with two interchangeable
implementations — `OpenAIContactExtractor` (Responses API) and
`GeminiContactExtractor` (Gemini `response_schema`). `build_extractor()` picks
one from `LLM_PROVIDER`; both return the same structured `ExtractionResponse`,
so the rest of the pipeline is unchanged. To use Gemini:

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-key-here
```

## REST API (Stage 7)

| Method & path                     | Description                          |
| --------------------------------- | ------------------------------------ |
| `GET /companies`                  | List companies (`?country=`)         |
| `GET /company/{id}`               | Single company                       |
| `GET /contacts`                   | List contacts                        |
| `GET /contacts?title=Certification` | Filter by title                    |
| `GET /contacts?country=Germany`   | Filter by country                    |
| `GET /contacts?company=u-blox`    | Filter by company                    |
| `GET /filings`                    | List filings (`?company_id=`)        |
| `GET /search?q=cyber`             | Free-text search over contacts       |
| `GET /export/contacts.csv`        | CSV export (Stage 8)                 |
| `POST /ingest`                    | Trigger a pipeline run for a company |
| `GET /ingest/{id}`                | Poll ingestion job status/report     |

## Priority scoring (Stage 9)

| Signal                              | Points |
| ----------------------------------- | ------ |
| Certification Manager               | +40    |
| Regulatory Affairs                  | +35    |
| Product Compliance                  | +30    |
| Product Security                    | +20    |
| Recent filing (< 2 years)           | +10    |
| Multiple filings                    | +5     |

Score is clamped to `0–100`.

## Classification (Stage 5)

Titles map to `CERTIFICATION_MANAGER`, `PRODUCT_COMPLIANCE`,
`REGULATORY_AFFAIRS`, `PRODUCT_SECURITY`, `QUALITY`, `ENGINEERING`, `EXECUTIVE`
or `IGNORE`. Only the first four are persisted. External lawyers, test labs and
certification bodies are dropped during extraction (Stage 4).

## Testing & quality

```bash
poetry run pytest --cov=app          # unit tests + coverage
poetry run ruff check .
poetry run mypy app
```

Tests run entirely offline against an in-memory SQLite database with a fake
OpenAI client and a fake HTTP client — no network or API key required.

## Extending to new sources (stretch goal)

`app/crawler/adapters.py` defines a `SourceAdapter` protocol and a registry.
Implement `find_applications` / `list_exhibits` for a new source (CE DoC, TÜV,
UL, SGS, Intertek, Eurofins, DEKRA), call `register_adapter(...)`, and the rest
of the extract → classify → dedupe → score pipeline works unchanged. The
corresponding `DocumentType` values already exist.

## Notes on the FCC data source

The FCC Equipment Authorization System (EAS) sits behind **Akamai Bot Manager**,
which blocks plain HTTP clients (403/503) — even with a spoofed TLS fingerprint —
because it requires a browser to run its JavaScript sensor. The crawler
therefore drives a headless **Firefox** via Playwright
([`app/crawler/browser_fetcher.py`](app/crawler/browser_fetcher.py)); Firefox
passes where headless Chrome is detected. Attachment downloads must send the
exhibit page as `Referer` or FCC returns 403.

Install the browser once:

```bash
poetry run playwright install firefox
```

HTML parsing is isolated in `app/crawler/parsing.py` and covered by tests
against **real captured EAS pages** (`tests/fixtures/`), so selectors can be
adjusted quickly if the markup changes. `FCC_MAX_FILINGS` (default 10) bounds how
many filings are processed per company. Please respect the FCC's terms of use
and rate limits.

### Where ingestion runs

The headless browser needs ~1 GB RAM, so ingestion (the crawl) is best run
**locally** or on a host with enough memory — not on a 512 MB free-tier web
service. Point it at your deployed database and it populates the cloud DB, which
the deployed API/frontend then serve:

```bash
DATABASE_URL='postgresql+psycopg://…(your Render Postgres)…' \
LLM_PROVIDER=gemini GEMINI_API_KEY=your-key \
poetry run python -m scripts.run_pipeline u-blox
```
