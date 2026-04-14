import logging
import os
import threading
from datetime import datetime, timezone
from html import escape

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from courtreserve_dome_checker import (
    build_court_time_ranges,
    fetch_available_slots,
    get_today_label,
    serialize_court_time_ranges,
)


LOGGER = logging.getLogger("courtreserve.api")
FETCH_LOCK = threading.Lock()


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_allowed_origins() -> list[str]:
    raw_value = os.getenv("ALLOW_ORIGINS", "*")
    origins = [value.strip() for value in raw_value.split(",") if value.strip()]
    return origins or ["*"]


configure_logging()

app = FastAPI(
    title="CourtReserve Dome Checker API",
    version="1.0.0",
    description="Production API for public pickleball court availability at The Dome.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/")
def home() -> HTMLResponse:
    return HTMLResponse(
        """
        <!DOCTYPE html>
        <html lang="en">
        <head>
          <meta charset="utf-8" />
          <meta name="viewport" content="width=device-width, initial-scale=1" />
          <title>CourtReserve Dome Checker</title>
          <style>
            body {
              font-family: Arial, sans-serif;
              max-width: 900px;
              margin: 40px auto;
              padding: 0 16px;
              line-height: 1.5;
              color: #1f2937;
            }
            h1 { margin-bottom: 8px; }
            code {
              background: #f3f4f6;
              padding: 2px 6px;
              border-radius: 4px;
            }
          </style>
        </head>
        <body>
          <h1>CourtReserve Dome Checker</h1>
          <p>Use <code>/available-times</code> for the HTML availability page.</p>
          <p>Use <code>/available-times.json</code> for the JSON API.</p>
          <p>Use <code>/health</code> for health checks.</p>
        </body>
        </html>
        """
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def fetch_availability_payload(show_browser: bool) -> dict[str, object]:
    with FETCH_LOCK:
        slots = fetch_available_slots(headless=not show_browser)
    court_ranges = build_court_time_ranges(slots)
    serialized_courts = serialize_court_time_ranges(court_ranges)
    total_ranges = sum(len(ranges) for ranges in serialized_courts.values())
    return {
        "date_label": get_today_label(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "court_count": len(serialized_courts),
        "range_count": total_ranges,
        "courts": serialized_courts,
    }


def render_availability_html(payload: dict[str, object]) -> str:
    date_label = escape(str(payload["date_label"]))
    generated_at = escape(str(payload["generated_at"]))
    courts = payload["courts"]
    assert isinstance(courts, dict)

    cards: list[str] = []
    for court_name, ranges in courts.items():
        assert isinstance(ranges, list)
        if ranges:
            items = "".join(
                (
                    "<li>"
                    f"<strong>{escape(str(time_range['label']))}</strong>"
                    f" <span>({escape(str(time_range['start']))} - {escape(str(time_range['end']))})</span>"
                    "</li>"
                )
                for time_range in ranges
            )
        else:
            items = "<li>No available times found.</li>"

        cards.append(
            f"""
            <section class="court-card">
              <h2>{escape(str(court_name))}</h2>
              <ul>{items}</ul>
            </section>
            """
        )

    cards_html = "".join(cards) or "<p>No courts were returned.</p>"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>Dome Pickleball Availability</title>
      <style>
        :root {{
          color-scheme: light;
        }}
        body {{
          margin: 0;
          font-family: Arial, sans-serif;
          background: linear-gradient(180deg, #f7fbff 0%, #eef6f2 100%);
          color: #17212b;
        }}
        .page {{
          max-width: 980px;
          margin: 0 auto;
          padding: 32px 16px 48px;
        }}
        .hero {{
          background: white;
          border-radius: 18px;
          padding: 24px;
          box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
          margin-bottom: 20px;
        }}
        .meta {{
          color: #4b5563;
          font-size: 14px;
        }}
        .courts {{
          display: grid;
          gap: 16px;
        }}
        .court-card {{
          background: white;
          border-radius: 18px;
          padding: 20px 24px;
          box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
        }}
        h1, h2 {{
          margin-top: 0;
        }}
        ul {{
          margin: 0;
          padding-left: 20px;
        }}
        li {{
          margin: 10px 0;
        }}
      </style>
    </head>
    <body>
      <main class="page">
        <section class="hero">
          <h1>Dome Pickleball Availability</h1>
          <p class="meta">Date: {date_label}</p>
          <p class="meta">Generated at: {generated_at}</p>
          <p class="meta">JSON version: <a href="/available-times.json">/available-times.json</a></p>
        </section>
        <section class="courts">
          {cards_html}
        </section>
      </main>
    </body>
    </html>
    """


@app.get("/available-times", response_class=HTMLResponse)
def available_times(
    show_browser: bool = Query(default=False, description="Debug only. Opens a visible browser."),
) -> HTMLResponse:
    try:
        payload = fetch_availability_payload(show_browser=show_browser)
        return HTMLResponse(render_availability_html(payload))
    except Exception as exc:
        LOGGER.exception("Failed to fetch court availability")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/available-times.json")
def available_times_json(
    show_browser: bool = Query(default=False, description="Debug only. Opens a visible browser."),
) -> dict[str, object]:
    try:
        return fetch_availability_payload(show_browser=show_browser)
    except Exception as exc:
        LOGGER.exception("Failed to fetch court availability")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
