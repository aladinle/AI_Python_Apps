import argparse
import queue
import re
import sys
import threading
import tkinter as tk
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from tkinter import ttk
from typing import Iterable


PUBLIC_WIDGET_URL = "https://widgets.courtreserve.com/Online/Public/EmbedCode/13095/41105"

TIME_PATTERN = re.compile(
    r"\b(?:1[0-2]|0?[1-9])(?::[0-5]\d)?\s?(?:AM|PM)\b",
    re.IGNORECASE,
)
COURT_PATTERN = re.compile(r"\b(?:court|crt)\s*#?\s*(\d+)\b", re.IGNORECASE)


@dataclass(frozen=True)
class TimeSlot:
    label: str
    source_text: str
    court_name: str | None = None


@dataclass(frozen=True)
class TimeRange:
    start_minutes: int
    end_minutes: int

    @property
    def label(self) -> str:
        return format_time_range(self.start_minutes, self.end_minutes)


ANTI_BOT_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });
Object.defineProperty(navigator, 'language', { get: () => 'en-US' });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
"""


def parse_available_slots(text_items: Iterable[str]) -> list[TimeSlot]:
    seen: set[str] = set()
    slots: list[TimeSlot] = []

    for raw_item in text_items:
        item = normalize_text(raw_item)
        if not item:
            continue
        if is_unavailable_text(item):
            continue

        matches = TIME_PATTERN.findall(item)
        if not matches:
            continue

        for match in matches:
            label = collapse_whitespace(match.upper())
            court_name = extract_court_name(item)
            dedupe_key = f"{court_name or 'unknown'}::{label}"
            if dedupe_key not in seen:
                seen.add(dedupe_key)
                slots.append(
                    TimeSlot(
                        label=label,
                        source_text=item,
                        court_name=court_name,
                    )
                )

    return sort_slots(slots)


def normalize_text(value: str) -> str:
    return collapse_whitespace(value.replace("\u00a0", " ").strip())


def collapse_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def is_unavailable_text(value: str) -> bool:
    lowered = value.lower()
    blocked_markers = (
        "unavailable",
        "not available",
        "booked",
        "reserved",
        "waitlist",
        "full",
        "closed",
        "cancelled",
        "canceled",
        "maintenance",
    )
    return any(marker in lowered for marker in blocked_markers)


def sort_slots(slots: list[TimeSlot]) -> list[TimeSlot]:
    return sorted(slots, key=lambda slot: time_label_to_minutes(slot.label))


def extract_court_name(value: str) -> str | None:
    match = COURT_PATTERN.search(value)
    if not match:
        return None
    return f"Court {match.group(1)}"


def time_label_to_minutes(label: str) -> int:
    match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s?(AM|PM)", label)
    if not match:
        return sys.maxsize

    hours = int(match.group(1)) % 12
    minutes = int(match.group(2) or 0)
    if match.group(3) == "PM":
        hours += 12
    return (hours * 60) + minutes


def build_time_ranges(slots: list[TimeSlot]) -> list[TimeRange]:
    if not slots:
        return []

    start_times = [time_label_to_minutes(slot.label) for slot in slots]
    step_minutes = infer_slot_duration(start_times)

    ranges: list[TimeRange] = []
    range_start = start_times[0]
    range_end = range_start + step_minutes

    for start_time in start_times[1:]:
        if start_time == range_end:
            range_end = start_time + step_minutes
            continue

        ranges.append(TimeRange(start_minutes=range_start, end_minutes=range_end))
        range_start = start_time
        range_end = start_time + step_minutes

    ranges.append(TimeRange(start_minutes=range_start, end_minutes=range_end))
    return ranges


def build_court_time_ranges(slots: list[TimeSlot]) -> dict[str, list[TimeRange]]:
    grouped_slots: dict[str, list[TimeSlot]] = {}
    for slot in slots:
        if not slot.court_name:
            continue
        grouped_slots.setdefault(slot.court_name, []).append(slot)

    court_ranges: dict[str, list[TimeRange]] = {}
    for court_name, court_slots in sorted(grouped_slots.items()):
        direct_ranges = [
            parsed_range
            for slot in court_slots
            if (parsed_range := parse_time_range_text(slot.source_text)) is not None
        ]
        if direct_ranges:
            court_ranges[court_name] = sorted(direct_ranges, key=lambda item: item.start_minutes)
            continue

        court_ranges[court_name] = build_time_ranges(sort_slots(court_slots))

    return court_ranges


def parse_time_range_text(value: str) -> TimeRange | None:
    matches = TIME_PATTERN.findall(value)
    if len(matches) < 2:
        compact_match = re.search(
            r"\b(\d{1,2}(?::\d{2})?)\s*-\s*(\d{1,2}(?::\d{2})?)\s*(AM|PM)\b",
            value,
            re.IGNORECASE,
        )
        if not compact_match:
            return None

        start_text = compact_match.group(1)
        end_text = compact_match.group(2)
        end_period = compact_match.group(3).upper()
        same_period_start = time_label_to_minutes(f"{start_text} {end_period}")
        end_minutes = time_label_to_minutes(f"{end_text} {end_period}")

        if same_period_start < end_minutes:
            return TimeRange(start_minutes=same_period_start, end_minutes=end_minutes)

        opposite_period = "PM" if end_period == "AM" else "AM"
        start_minutes = time_label_to_minutes(f"{start_text} {opposite_period}")
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        return TimeRange(start_minutes=start_minutes, end_minutes=end_minutes)

    start_minutes = time_label_to_minutes(collapse_whitespace(matches[0].upper()))
    end_minutes = time_label_to_minutes(collapse_whitespace(matches[1].upper()))
    if end_minutes <= start_minutes:
        end_minutes += 24 * 60
    return TimeRange(start_minutes=start_minutes, end_minutes=end_minutes)


def build_available_time_ranges(
    visible_range: TimeRange,
    reservations: list[TimeRange],
) -> list[TimeRange]:
    if visible_range.end_minutes <= visible_range.start_minutes:
        return []

    normalized: list[TimeRange] = []
    for reservation in sorted(reservations, key=lambda item: item.start_minutes):
        start = max(visible_range.start_minutes, reservation.start_minutes)
        end = min(visible_range.end_minutes, reservation.end_minutes)
        if end <= start:
            continue

        if normalized and start <= normalized[-1].end_minutes:
            previous = normalized[-1]
            normalized[-1] = TimeRange(
                start_minutes=previous.start_minutes,
                end_minutes=max(previous.end_minutes, end),
            )
            continue

        normalized.append(TimeRange(start_minutes=start, end_minutes=end))

    available: list[TimeRange] = []
    cursor = visible_range.start_minutes
    for reservation in normalized:
        if reservation.start_minutes > cursor:
            available.append(TimeRange(start_minutes=cursor, end_minutes=reservation.start_minutes))
        cursor = max(cursor, reservation.end_minutes)

    if cursor < visible_range.end_minutes:
        available.append(TimeRange(start_minutes=cursor, end_minutes=visible_range.end_minutes))

    return available


def build_court_ranges_from_schedule_snapshot(snapshot: Mapping[str, object]) -> dict[str, list[TimeRange]]:
    visible_start = str(snapshot.get("visibleStart") or "")
    visible_end = str(snapshot.get("visibleEnd") or "")
    slot_duration_minutes = int(snapshot.get("slotDurationMinutes") or 0)
    visible_range = parse_time_range_text(f"{visible_start} {visible_end}")
    if not visible_range and visible_start and slot_duration_minutes > 0:
        start_minutes = time_label_to_minutes(collapse_whitespace(visible_start.upper()))
        visible_range = TimeRange(
            start_minutes=start_minutes,
            end_minutes=start_minutes + slot_duration_minutes,
        )
    if not visible_range:
        return {}

    court_ranges: dict[str, list[TimeRange]] = {}
    courts = snapshot.get("courts")
    if not isinstance(courts, list):
        return court_ranges

    for court in courts:
        if not isinstance(court, Mapping):
            continue

        court_name = collapse_whitespace(str(court.get("name") or ""))
        if not court_name:
            continue

        reservations: list[TimeRange] = []
        for raw_event in court.get("reservations", []):
            if not raw_event:
                continue
            event_range = parse_time_range_text(str(raw_event))
            if event_range:
                reservations.append(event_range)

        available_ranges = build_available_time_ranges(visible_range, reservations)
        if available_ranges:
            court_ranges[court_name] = available_ranges

    return court_ranges


def infer_slot_duration(start_times: list[int]) -> int:
    positive_gaps = [
        current - previous
        for previous, current in zip(start_times, start_times[1:])
        if current > previous
    ]
    if not positive_gaps:
        return 60
    return min(positive_gaps)


def format_time_range(start_minutes: int, end_minutes: int) -> str:
    start_hour, start_minute, start_period = minutes_to_clock_parts(start_minutes)
    end_hour, end_minute, end_period = minutes_to_clock_parts(end_minutes)

    start_text = format_clock_time(
        start_hour,
        start_minute,
        period=start_period,
        include_period=start_period != end_period,
    )
    end_text = format_clock_time(end_hour, end_minute, period=end_period, include_period=True)
    return f"{start_text}-{end_text}"


def minutes_to_clock_parts(total_minutes: int) -> tuple[int, int, str]:
    total_minutes %= 24 * 60
    hours_24, minutes = divmod(total_minutes, 60)
    period = "AM" if hours_24 < 12 else "PM"
    hours_12 = hours_24 % 12 or 12
    return hours_12, minutes, period


def format_clock_time(hour: int, minute: int, period: str, include_period: bool) -> str:
    minute_text = f":{minute:02d}" if minute else ""
    suffix = period if include_period else ""
    return f"{hour}{minute_text}{suffix}"


def get_today_label() -> str:
    return datetime.now().strftime("%A, %B %d")


def fetch_available_slots(headless: bool = True) -> list[TimeSlot]:
    try:
        from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Run `pip install -r requirements.txt` and "
            "`python -m playwright install chromium` first."
        ) from exc

    try:
        with sync_playwright() as playwright:
            launch_options = {
                "headless": headless,
                "args": ["--disable-blink-features=AutomationControlled"],
            }
            try:
                browser = playwright.chromium.launch(channel="chrome", **launch_options)
            except Exception:
                browser = playwright.chromium.launch(**launch_options)

            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/135.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1800, "height": 1400},
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            page = context.new_page()
            page.add_init_script(ANTI_BOT_INIT_SCRIPT)
            try:
                return fetch_dome_pickleball_slots(page)
            finally:
                context.close()
                browser.close()
    except PlaywrightTimeoutError as exc:
        raise RuntimeError(f"Timed out while loading The Dome pages: {exc}") from exc


def fetch_dome_pickleball_slots(page) -> list[TimeSlot]:
    page.goto(PUBLIC_WIDGET_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("networkidle")
    page.wait_for_selector("#CourtsScheduler .k-scheduler-layout", timeout=60000)
    try:
        page.wait_for_selector("#CourtsScheduler .k-scheduler-content .k-event", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(3000)

    schedule_snapshot = page.evaluate(
        """
        () => {
          const text = (element) => (element?.innerText || '')
            .replace(/\\u200b/g, ' ')
            .replace(/\\u00a0/g, ' ')
            .replace(/\\s+/g, ' ')
            .trim();

          const timePattern = /\\b(?:1[0-2]|0?[1-9])(?::[0-5]\\d)?\\s?(?:AM|PM)\\b/i;
          const toMinutes = (label) => {
            const match = label.match(/(\\d{1,2})(?::(\\d{2}))?\\s?(AM|PM)/i);
            if (!match) {
              return null;
            }
            let hours = Number(match[1]) % 12;
            const minutes = Number(match[2] || 0);
            if (match[3].toUpperCase() === 'PM') {
              hours += 12;
            }
            return (hours * 60) + minutes;
          };
          const toLabel = (totalMinutes) => {
            const normalized = ((totalMinutes % 1440) + 1440) % 1440;
            const hours24 = Math.floor(normalized / 60);
            const minutes = normalized % 60;
            const period = hours24 < 12 ? 'AM' : 'PM';
            const hours12 = (hours24 % 12) || 12;
            const minuteText = minutes ? `:${String(minutes).padStart(2, '0')}` : ':00';
            return `${hours12}${minuteText} ${period}`;
          };
          const schedulerContent = document.querySelector('#CourtsScheduler .k-scheduler-content');
          if (schedulerContent) {
            schedulerContent.scrollTop = 0;
          }

          const headers = Array.from(document.querySelectorAll('#CourtsScheduler .k-scheduler-group-cell'))
            .map((cell) => ({
              name: text(cell.querySelector('.court-group-header') || cell),
              left: cell.getBoundingClientRect().left,
              right: cell.getBoundingClientRect().right
            }))
            .filter((header) => header.name);

          const allLabels = Array.from(document.querySelectorAll('#CourtsScheduler .k-scheduler-times .fn-kendo-time'))
            .map((label) => ({
              text: text(label),
              top: label.getBoundingClientRect().top,
              bottom: label.getBoundingClientRect().bottom
            }))
            .filter((label) => timePattern.test(label.text));
          allLabels.sort((a, b) => a.top - b.top);
          const slotDurationMinutes = Number(window.interval || 30);
          const visibleStart = allLabels[0]?.text || '';
          const lastLabel = allLabels[allLabels.length - 1]?.text || '';
          const lastLabelMinutes = toMinutes(lastLabel);
          const visibleEnd = lastLabelMinutes === null
            ? ''
            : toLabel(lastLabelMinutes + slotDurationMinutes);

          const reservationsByCourt = new Map(headers.map((header) => [header.name, []]));
          const seenEvents = new Set();

          for (const eventNode of document.querySelectorAll('#CourtsScheduler .k-scheduler-content .k-event')) {
            const timeText = text(eventNode.querySelector('.event-time')) || text(eventNode);
            if (!timePattern.test(timeText)) {
              continue;
            }
            const eventDetails = text(eventNode.querySelector('.reservation-container') || eventNode);
            const eventText = `${timeText} ${eventDetails}`.trim();

            const rect = eventNode.getBoundingClientRect();
            const midpoint = rect.left + (rect.width / 2);
            const matchedCourt = headers.find(
              (header) => midpoint >= header.left && midpoint <= header.right
            );
            if (!matchedCourt) {
              continue;
            }

            const eventKey = `${matchedCourt.name}::${eventText}`;
            if (seenEvents.has(eventKey)) {
              continue;
            }

            seenEvents.add(eventKey);
            reservationsByCourt.get(matchedCourt.name).push(eventText);
          }

          return {
            visibleStart,
            visibleEnd,
            slotDurationMinutes,
            courts: headers.map((header) => ({
              name: header.name,
              reservations: reservationsByCourt.get(header.name) || []
            }))
          };
        }
        """
    )

    court_ranges = build_court_ranges_from_schedule_snapshot(schedule_snapshot)
    if court_ranges:
        slots: list[TimeSlot] = []
        for court_name, ranges in court_ranges.items():
            for time_range in ranges:
                slots.append(
                    TimeSlot(
                        label=format_clock_time(*minutes_to_clock_parts(time_range.start_minutes), include_period=True),
                        source_text=time_range.label,
                        court_name=court_name,
                    )
                )
        return slots

    clickable_texts = page.evaluate(
        """
        () => {
          const isVisible = (element) => {
            const style = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            return style.visibility !== 'hidden' &&
              style.display !== 'none' &&
              rect.width > 0 &&
              rect.height > 0;
          };

          return Array.from(document.querySelectorAll('button, a, [role="button"], td, div, span, li'))
            .filter(isVisible)
            .map((element) => (element.innerText || '').trim())
            .filter(Boolean)
            .filter((text) => /\\b(?:1[0-2]|0?[1-9])(?::[0-5]\\d)?\\s?(?:AM|PM)\\b/i.test(text));
        }
        """
    )

    slots = parse_available_slots(clickable_texts)
    if slots:
        return slots

    fallback_text = page.locator("body").inner_text()
    return parse_available_slots(fallback_text.splitlines())


def print_slots(slots: list[TimeSlot]) -> None:
    if not slots:
        print(f"No available pickleball court times were detected for {get_today_label()}.")
        return

    court_ranges = build_court_time_ranges(slots)
    if not court_ranges:
        print(f"No available pickleball court times were detected for {get_today_label()}.")
        return

    print(f"Available pickleball court times for {get_today_label()}:")
    for court_name, ranges in court_ranges.items():
        print(f"{court_name}:")
        for time_range in ranges:
            print(f"- {time_range.label}")


class DomeCheckerApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("The Dome Pickleball Times")
        self.root.geometry("460x520")
        self.root.minsize(420, 420)

        self.results_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.loading = False

        self.title_var = tk.StringVar(value=f"Today's availability: {get_today_label()}")
        self.status_var = tk.StringVar(value="Loading today's available court times...")

        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="The Dome Pickleball Courts",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")

        ttk.Label(
            container,
            textvariable=self.title_var,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 10))

        ttk.Button(
            container,
            text="Refresh Today's Times",
            command=self.refresh_slots,
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(
            container,
            textvariable=self.status_var,
            wraplength=400,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(0, 10))

        self.slots_list = tk.Text(
            container,
            font=("Consolas", 14),
            height=14,
            wrap="word",
            state="disabled",
        )
        self.slots_list.pack(fill="both", expand=True)

        note = (
            "Times are fetched from The Dome's public CourtReserve booking page. "
            "The browser stays hidden while the app loads the results."
        )
        ttk.Label(
            container,
            text=note,
            wraplength=400,
            font=("Segoe UI", 9),
        ).pack(anchor="w", pady=(12, 0))

        self.root.after(200, self._poll_results)
        self.refresh_slots()

    def refresh_slots(self) -> None:
        if self.loading:
            return

        self.loading = True
        self.title_var.set(f"Today's availability: {get_today_label()}")
        self.status_var.set("Loading today's available pickleball court times...")
        self._set_results_text("Loading...")

        worker = threading.Thread(target=self._load_slots_worker, daemon=True)
        worker.start()

    def _load_slots_worker(self) -> None:
        try:
            slots = fetch_available_slots(headless=True)
            self.results_queue.put(("success", slots))
        except Exception as exc:
            self.results_queue.put(("error", str(exc)))

    def _poll_results(self) -> None:
        try:
            while True:
                status, payload = self.results_queue.get_nowait()
                self.loading = False
                if status == "success":
                    self._show_slots(payload)
                else:
                    self._show_error(payload)
        except queue.Empty:
            pass

        self.root.after(200, self._poll_results)

    def _show_slots(self, slots: list[TimeSlot]) -> None:
        court_ranges = build_court_time_ranges(slots)

        if court_ranges:
            lines: list[str] = []
            total_ranges = 0
            for court_name, ranges in court_ranges.items():
                total_ranges += len(ranges)
                lines.append(court_name)
                for time_range in ranges:
                    lines.append(f"  {time_range.label}")
                lines.append("")

            self._set_results_text("\n".join(lines).strip())
            self.status_var.set(
                f"Found {total_ranges} available time range(s) across {len(court_ranges)} court(s) today."
            )
            return

        self._set_results_text("No available time slots found.")
        self.status_var.set("No public pickleball court times were detected for today.")

    def _show_error(self, message: str) -> None:
        self._set_results_text("Unable to load times.")
        self.status_var.set(message)

    def _set_results_text(self, value: str) -> None:
        self.slots_list.configure(state="normal")
        self.slots_list.delete("1.0", tk.END)
        self.slots_list.insert("1.0", value)
        self.slots_list.configure(state="disabled")

    def run(self) -> None:
        self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Show today's public pickleball court times for The Dome."
    )
    parser.add_argument(
        "--cli",
        action="store_true",
        help="Print the available times to the terminal instead of opening the desktop app.",
    )
    parser.add_argument(
        "--show-browser",
        action="store_true",
        help="Open Chromium visibly for debugging instead of using the hidden browser.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.cli:
        try:
            slots = fetch_available_slots(headless=not args.show_browser)
        except RuntimeError as exc:
            print(str(exc))
            return 1
        print_slots(slots)
        return 0 if slots else 2

    app = DomeCheckerApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
