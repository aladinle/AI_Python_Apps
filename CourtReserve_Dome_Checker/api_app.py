import logging
import os
import threading
from datetime import datetime, timezone
from html import escape
from time import monotonic

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
CACHE_LOCK = threading.Lock()
CACHE_TTL_SECONDS = max(1, int(os.getenv("CACHE_TTL_SECONDS", "180")))
MAX_STALE_SECONDS = max(CACHE_TTL_SECONDS, int(os.getenv("MAX_STALE_SECONDS", "900")))


_cache_payload: dict[str, object] | None = None
_cache_fetched_at_monotonic: float | None = None
_refresh_in_progress = False


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def parse_allowed_origins() -> list[str]:
    raw_value = os.getenv("ALLOW_ORIGINS", "*")
    origins = [value.strip() for value in raw_value.split(",") if value.strip()]
    return origins or ["*"]


def get_cache_age_seconds() -> float | None:
    with CACHE_LOCK:
        if _cache_fetched_at_monotonic is None:
            return None
        return max(0.0, monotonic() - _cache_fetched_at_monotonic)


def get_cached_payload() -> tuple[dict[str, object] | None, float | None]:
    with CACHE_LOCK:
        if _cache_payload is None or _cache_fetched_at_monotonic is None:
            return None, None
        return dict(_cache_payload), max(0.0, monotonic() - _cache_fetched_at_monotonic)


def store_cached_payload(payload: dict[str, object]) -> None:
    global _cache_payload, _cache_fetched_at_monotonic
    with CACHE_LOCK:
        _cache_payload = dict(payload)
        _cache_fetched_at_monotonic = monotonic()


def mark_refresh_started() -> bool:
    global _refresh_in_progress
    with CACHE_LOCK:
        if _refresh_in_progress:
            return False
        _refresh_in_progress = True
        return True


def mark_refresh_finished() -> None:
    global _refresh_in_progress
    with CACHE_LOCK:
        _refresh_in_progress = False


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


def refresh_cache(show_browser: bool = False) -> dict[str, object]:
    try:
        payload = fetch_availability_payload(show_browser=show_browser)
        store_cached_payload(payload)
        return payload
    finally:
        mark_refresh_finished()


def refresh_cache_in_background(show_browser: bool = False) -> None:
    if not mark_refresh_started():
        return

    def worker() -> None:
        try:
            refresh_cache(show_browser=show_browser)
        except Exception:
            LOGGER.exception("Background cache refresh failed")

    threading.Thread(target=worker, daemon=True).start()


def get_availability_payload(force_refresh: bool = False, show_browser: bool = False) -> dict[str, object]:
    cached_payload, cache_age_seconds = get_cached_payload()
    if not force_refresh and cached_payload is not None and cache_age_seconds is not None:
        cached_payload["cached"] = True
        cached_payload["cache_age_seconds"] = round(cache_age_seconds, 1)
        if cache_age_seconds <= CACHE_TTL_SECONDS:
            return cached_payload
        if cache_age_seconds <= MAX_STALE_SECONDS:
            refresh_cache_in_background(show_browser=show_browser)
            return cached_payload

    if not mark_refresh_started():
        cached_payload, cache_age_seconds = get_cached_payload()
        if cached_payload is not None and cache_age_seconds is not None:
            cached_payload["cached"] = True
            cached_payload["cache_age_seconds"] = round(cache_age_seconds, 1)
            return cached_payload
        raise RuntimeError("Availability refresh is already in progress. Please retry in a moment.")

    payload = refresh_cache(show_browser=show_browser)
    payload["cached"] = False
    payload["cache_age_seconds"] = 0.0
    return payload


def render_availability_html(payload: dict[str, object]) -> str:
    date_label = escape(str(payload["date_label"]))
    generated_at = escape(str(payload["generated_at"]))
    cache_age_seconds = escape(str(payload.get("cache_age_seconds", 0.0)))
    cached_text = "yes" if payload.get("cached") else "no"
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
          <p class="meta">Cached response: {cached_text}</p>
          <p class="meta">Cache age: {cache_age_seconds} seconds</p>
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
    force_refresh: bool = Query(default=False, description="Bypass cache and fetch live availability."),
) -> HTMLResponse:
    try:
        payload = get_availability_payload(force_refresh=force_refresh, show_browser=show_browser)
        return HTMLResponse(render_availability_html(payload))
    except Exception as exc:
        LOGGER.exception("Failed to fetch court availability")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/available-times.json")
def available_times_json(
    show_browser: bool = Query(default=False, description="Debug only. Opens a visible browser."),
    force_refresh: bool = Query(default=False, description="Bypass cache and fetch live availability."),
) -> dict[str, object]:
    try:
        return get_availability_payload(force_refresh=force_refresh, show_browser=show_browser)
    except Exception as exc:
        LOGGER.exception("Failed to fetch court availability")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


app.add_event_handler("startup", lambda: refresh_cache_in_background(show_browser=False))
