# CourtReserve Dome Checker

This project fetches public pickleball court availability from The Dome's CourtReserve widget and exposes it in two ways:

- a local desktop/CLI script for development
- a FastAPI service that is ready to deploy to Render

## Local setup

```bash
cd "D:\Self Projects\AI_Python_Apps\CourtReserve_Dome_Checker"
pip install -r requirements.txt
python -m playwright install chromium
```

## Local run modes

Desktop UI:

```bash
python courtreserve_dome_checker.py
```

CLI:

```bash
python courtreserve_dome_checker.py --cli
```

API:

```bash
uvicorn api_app:app --host 0.0.0.0 --port 8000
```

Then open `http://localhost:8000/available-times`.

## Render deployment

This folder now includes a production `Dockerfile` and `render.yaml`.

If this project lives inside a larger monorepo, set Render's Root Directory to `CourtReserve_Dome_Checker`.

### Recommended Render settings

- Environment: `Docker`
- Health check path: `/health`
- Start command: provided by the `Dockerfile`

### Optional environment variables

```bash
ALLOW_ORIGINS=*
LOG_LEVEL=INFO
COURTRESERVE_NAVIGATION_TIMEOUT_MS=90000
COURTRESERVE_SELECTOR_TIMEOUT_MS=90000
COURTRESERVE_POST_LOAD_WAIT_MS=2500
COURTRESERVE_FETCH_RETRIES=2
```

## API response shape

`GET /available-times`

```json
{
  "date_label": "Tuesday, April 14",
  "generated_at": "2026-04-14T19:00:00+00:00",
  "court_count": 2,
  "range_count": 3,
  "courts": {
    "Pickleball Court #1 (Pickleball)": [
      { "start": "08:00", "end": "19:00", "label": "8AM-7PM" }
    ]
  }
}
```

## Notes

- The scraper runs headless in production and does not require the desktop UI.
- Tkinter is optional now, so the API can start on Linux hosts like Render even when GUI libraries are unavailable.
- The browser stays hidden by default. `show_browser=true` is only for local debugging.
- The scraper no longer waits for Playwright `networkidle`, because CourtReserve keeps background connections open and that can cause false timeouts on Render.
- If CourtReserve changes the widget markup, the selector logic may need a refresh.
