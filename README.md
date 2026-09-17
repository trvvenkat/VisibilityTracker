# Visibility Check Tracker

A local-first, full-stack web application that automates checking product visibility for a list of keywords against **Amazon** and **Flipkart**.

The user uploads a CSV/XLS/XLSX file containing search terms, configures the platform and target number of sponsored listings ($N$), and the application searches **one keyword at a time**, extracts sponsored product listings ($SP_1 \dots SP_N$) and separate sponsored display placements in their displayed order, and **incrementally streams results to a live CSV** while broadcasting real-time progress to a web dashboard.

---

## Key Features

- **Local-First & Lightweight**: Zero external database, Redis, Celery, or cloud infrastructure. Runs completely locally on Python 3.11+.
- **Sequential Automation**: Executes searches one keyword at a time using Playwright to mimic natural browsing patterns.
- **Incremental Live CSV Flushing**: Appends and flushes (`os.fsync`) every result immediately after each keyword. If interrupted or crashed, partial results are never lost.
- **Configurable $N$**: Supports any positive integer $N$ (default 3), dynamically building output headers (`KW,SP1,SP2,...,SPN,Sponsored Display`).
- **Sponsored Display Detection**: Specifically distinguishes normal product grid sponsored listings from dedicated Sponsored Brand / Display banners above or separate from results.
- **Fault-Tolerant & Isolated**: Individual keyword errors (timeouts, network hiccups) are recorded as `N/A` rows and do not terminate the job.
- **Bot / CAPTCHA Detection**: Detects CAPTCHA and block pages gracefully, capturing diagnostics without attempting illegal bypasses.
- **Real-Time Web Dashboard**: Server-Sent Events (SSE) with resilient fallback polling, live progress bar, keyword ticker, dynamic table rendering, and downloadable live CSV at any time.

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      Jinja2 + Vanilla JS UI                 │
│  (Drag-and-Drop, SSE EventSource, Dynamic Table, Controls)   │
└──────────────┬───────────────────────────────▲──────────────┘
               │ HTTP POST /api/upload         │ SSE /api/jobs/{id}/events
               │ HTTP POST /api/jobs           │ Polling /api/jobs/{id}/status
               ▼                               │
┌──────────────────────────────────────────────┴──────────────┐
│                    FastAPI Backend Engine                   │
│                                                             │
│  ┌────────────────────┐          ┌───────────────────────┐  │
│  │ File Parser        │          │ In-Memory Job Manager │  │
│  │ (CSV, XLS, XLSX)   │          │ (UUID, State, Queues) │  │
│  └────────┬───────────┘          └───────────▲───────────┘  │
│           │ Keywords                         │ Status / Row │
│           ▼                                  │              │
│  ┌───────────────────────────────────────────┴───────────┐  │
│  │         Visibility Checker Runner (Sequential)         │  │
│  │                                                       │  │
│  │     Keyword N                                         │  │
│  │        ↓                                              │  │
│  │  ┌───────────────┐     Row     ┌───────────────────┐  │  │
│  │  │   Scraper     ├────────────►│  Live CSV Writer  │  │  │
│  │  │  (Playwright) │             │ (flush + fsync)   │  │  │
│  │  └───────┬───────┘             └─────────┬─────────┘  │  │
│  └──────────┼───────────────────────────────┼────────────┘  │
└─────────────┼───────────────────────────────┼───────────────┘
              ▼                               ▼
       Amazon / Flipkart              data/jobs/{id}/results.csv
```

---

## Directory Structure

```text
VisibilityTracker/
├── app/
│   ├── main.py                     # FastAPI application & lifecycle
│   ├── config.py                   # Pydantic Settings & environment variables
│   ├── api/
│   │   ├── upload.py               # POST /api/upload endpoint
│   │   └── jobs.py                 # POST /api/jobs, GET status, results, download, SSE
│   ├── scrapers/
│   │   ├── base.py                 # PlatformScraper ABC, SearchResult, SponsoredProduct
│   │   ├── amazon.py               # Amazon Playwright scraper & isolated selectors
│   │   ├── flipkart.py             # Flipkart Playwright scraper & isolated selectors
│   │   └── mock.py                 # Mock scraper for offline testing & rapid CI
│   ├── services/
│   │   ├── file_parser.py          # CSV/XLS/XLSX keyword extraction & validation
│   │   ├── csv_writer.py           # Thread-safe incremental flushed CSV writer
│   │   ├── job_manager.py          # In-memory job state & SSE subscriber dispatcher
│   │   └── visibility_checker.py   # Sequential execution engine & lifecycle control
│   ├── schemas/
│   │   └── job.py                  # Pydantic request/response schemas
│   ├── templates/
│   │   └── index.html              # Jinja2 dashboard UI
│   └── static/
│       ├── css/style.css           # Modern dark-mode glassmorphic design system
│       └── js/app.js               # Frontend controller, drag-drop, SSE & live table
├── data/
│   ├── uploads/                    # Stored input files
│   └── jobs/                       # Per-job directories with results.csv
├── tests/
│   ├── test_file_parser.py         # File formats, empty files, normalization
│   ├── test_csv_writer.py          # Dynamic headers, N=1,3,5, row flush
│   ├── test_job_manager.py         # Job lifecycle, cancellation, state
│   ├── test_scrapers_mock.py       # MockScraper validation & failure handling
│   ├── test_scrapers_fixtures.py   # Amazon & Flipkart HTML parsing tests
│   ├── test_visibility_checker.py  # Sequential run & disk CSV verification
│   └── test_api.py                 # End-to-end API integration tests
├── requirements.txt
├── pytest.ini
├── README.md
└── .gitignore
```

---

## Installation & Setup

### Prerequisites

- **Python 3.11+**
- macOS, Linux, or Windows

### 1. Clone & Set Up Virtual Environment

```bash
cd VisibilityTracker
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Install Playwright Browsers

```bash
playwright install chromium
```

---

## Running the Application

Start the local server with:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:

```text
http://127.0.0.1:8000
```

---

## Configuration Options

Settings can be customized via a `.env` file in the project root or through environment variables:

| Variable | Default | Description |
|---|---|---|
| `BROWSER_HEADLESS` | `false` | Set to `false` for interactive browser window, or `true` for headless |
| `DEFAULT_TOP_N` | `3` | Default number of sponsored product listings to capture |
| `NAVIGATION_TIMEOUT`| `30000` | Page navigation timeout in milliseconds |
| `SEARCH_TIMEOUT` | `30000` | Search result container timeout in milliseconds |
| `DELAY_BETWEEN_KEYWORDS` | `2.0` | Delay (seconds) between sequential searches on live platforms |
| `AMAZON_BASE_URL` | `https://www.amazon.in` | Base URL for Amazon searches (`.in` or `.com`) |
| `FLIPKART_BASE_URL`| `https://www.flipkart.com` | Base URL for Flipkart searches |

---

## Supported Input Formats

The upload handler accepts `.csv`, `.xls`, and `.xlsx` files containing search terms.

### Keyword Column Discovery Rules:
1. Matches case-insensitive candidate column headers: `keyword`, `keywords`, `kw`, `search_term`, `query`, `product`.
2. If no candidate header exists, automatically uses the first non-empty text column.
3. Completely empty rows and duplicate consecutive blank lines are ignored.
4. Surrounding whitespace is trimmed from each keyword.

Example CSV:
```csv
keyword
iphone 17
samsung s26
macbook air
airpods
wireless headphones
```

---

## Output CSV Format

The output CSV header is dynamically constructed based on $N$:

### For $N = 3$:
```text
KW,SP1,SP2,SP3,Sponsored Display
```

### Sample Output:
```csv
KW,SP1,SP2,SP3,Sponsored Display
iphone 17,Apple iPhone 17 Case,Spigen iPhone Case,ESR iPhone Case,N/A
samsung s26,Samsung Cover,Spigen Case,N/A,Official Samsung Store Banner
macbook air,Product A,Product B,Product C,N/A
```

- If fewer than $N$ sponsored listings exist, missing positions are marked as `N/A`.
- If a Sponsored Display banner does not exist, it is marked as `N/A`.
- If a keyword search fails (e.g. timeout or bot challenge), a row of `N/A`s is recorded.

---

## Platform Scraper Details & Updating Selectors

All selectors are strictly isolated in platform-specific scraper classes:

### Amazon Scraper (`app/scrapers/amazon.py`)
- **Search Input**: `#twotabsearchtextbox`
- **Result Containers**: `div[data-component-type='s-search-result']`, `div.s-result-item[data-asin]`
- **Sponsored Badges**: `.puis-sponsored-label-text`, `span:text-is('Sponsored')`, `[aria-label*='Sponsored']`
- **Titles**: `h2 a.a-link-normal span`, `h2 a span`, `h2 span`
- **Sponsored Display / Brands**: `div[data-component-type='sp-sponsored-brands']`, `div[data-component-type='s-head-to-foot-slot']`
- **CAPTCHA Challenge**: `form[action*='validateCaptcha']`, `#captchacharacters`, `text='Robot Check'`

### Flipkart Scraper (`app/scrapers/flipkart.py`)
- **Search Input**: `input[name='q']`, `input.Pke_EE`
- **Result Containers**: `div.cPHDOP[data-id]`, `div._1AtVbE[data-id]`, `div[data-id]`
- **Sponsored Badges**: `div:text-is('Ad')`, `span:text-is('Ad')`, `div:text-is('Sponsored')`
- **Titles**: `div._4rR01T`, `div.KzDlHZ`, `a.s1Q9rs`, `a.wByabb`
- **Sponsored Display**: `div._1yR-bH`, `div._2d0fq9`

To update selectors when Amazon or Flipkart changes their DOM structure, edit the class attributes at the top of `app/scrapers/amazon.py` or `app/scrapers/flipkart.py`.

---

## Limitations & Anti-Bot Notes

- **Anti-Bot & CAPTCHAs**: Neither Amazon nor Flipkart provides a public, unauthenticated scraping API. If requests are submitted too aggressively, IP blocks or CAPTCHA challenges ("Robot Check") may appear.
- **Handling Strategy**: The application **does not** attempt to solve or bypass CAPTCHAs. Instead, it detects the challenge, logs an error diagnostic, writes `N/A` for the keyword row, and continues to the next keyword.
- **Recommended Practice**:
  - Keep `DELAY_BETWEEN_KEYWORDS` at 2–3 seconds.
  - Run the browser in headed mode (`BROWSER_HEADLESS=false`) for visual monitoring.
  - Use moderate keyword batch sizes (e.g., 20–100 keywords per job).

---

## Testing

Run the automated test suite with:

```bash
pytest -v
```

All 24 unit and integration tests validate:
- CSV, XLS, XLSX parsing & validation
- Dynamic CSV headers and immediate disk flushing
- Job manager state transitions and cancellation
- Mock scraper execution and error simulation
- Mocked HTML DOM fixtures for Amazon and Flipkart
- End-to-end API endpoints
