import logging
import os
import threading
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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
def home() -> dict[str, object]:
    return {
        "service": "courtreserve-dome-checker",
        "status": "ok",
        "endpoints": ["/health", "/available-times"],
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/available-times")
def available_times(
    show_browser: bool = Query(default=False, description="Debug only. Opens a visible browser."),
) -> dict[str, object]:
    try:
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
    except Exception as exc:
        LOGGER.exception("Failed to fetch court availability")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
