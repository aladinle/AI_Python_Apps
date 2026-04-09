from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# import from your existing file
from courtreserve_dome_checker import (
    fetch_available_slots,
    build_court_time_ranges,
    get_today_label,
)

app = FastAPI(title="Dome Pickleball API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "message": "Dome Pickleball Checking API is running"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/available-times")
def available_times(show_browser: bool = False):
    try:
        slots = fetch_available_slots(headless=not show_browser)
        court_ranges = build_court_time_ranges(slots)

        result = {
            "date": get_today_label(),
            "courts": {}
        }

        for court_name, ranges in court_ranges.items():
            result["courts"][court_name] = [r.label for r in ranges]

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))