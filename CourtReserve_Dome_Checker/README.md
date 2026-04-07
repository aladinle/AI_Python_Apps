# CourtReserve Dome Checker

This app shows today's public pickleball court times for The Dome in a simple desktop window. It uses a hidden browser in the background, so users do not need to watch or interact with the CourtReserve page, groups contiguous slots into readable ranges such as `8-10AM` or `1-5PM`, and displays availability separately for each court.

## Setup

```bash
cd "D:\Self Projects\AI_Python_Apps\CourtReserve_Dome_Checker"
pip install -r requirements.txt
python -m playwright install chromium
```

## Run

```bash
python courtreserve_dome_checker.py
```

That opens the desktop app and loads today's available time slots.

If you want terminal output instead:

```bash
python courtreserve_dome_checker.py --cli
```

## Notes

- The Dome reservation page currently links into a public CourtReserve widget for pickleball court availability.
- No CourtReserve login is required.
- The browser stays hidden by default. `--show-browser` is only for debugging.
- If The Dome or CourtReserve changes the page markup, the selectors in the script may need a small refresh.
