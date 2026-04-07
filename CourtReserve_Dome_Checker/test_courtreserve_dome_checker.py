from courtreserve_dome_checker import (
    build_available_time_ranges,
    build_court_time_ranges,
    build_court_ranges_from_schedule_snapshot,
    build_time_ranges,
    parse_time_range_text,
    TimeRange,
    parse_available_slots,
    time_label_to_minutes,
)


def test_parse_available_slots_filters_unavailable_entries():
    text_items = [
        "8:00 AM",
        "Reserved 9:00 AM",
        "10:30 AM Court 1",
        "11:00 AM unavailable",
        "12:15 PM",
    ]

    slots = parse_available_slots(text_items)

    assert [slot.label for slot in slots] == ["8:00 AM", "10:30 AM", "12:15 PM"]


def test_parse_available_slots_deduplicates_and_sorts():
    text_items = [
        "2:00 PM",
        "9:30 AM",
        "2:00 PM",
        "11:00 AM",
    ]

    slots = parse_available_slots(text_items)

    assert [slot.label for slot in slots] == ["9:30 AM", "11:00 AM", "2:00 PM"]


def test_time_label_to_minutes_handles_noon_and_midnight():
    assert time_label_to_minutes("12:00 AM") == 0
    assert time_label_to_minutes("12:00 PM") == 12 * 60


def test_build_time_ranges_groups_consecutive_hour_slots():
    slots = parse_available_slots(
        [
            "8:00 AM Court 1",
            "9:00 AM Court 1",
            "1:00 PM Court 2",
            "2:00 PM Court 2",
            "3:00 PM Court 2",
            "4:00 PM Court 2",
        ]
    )

    ranges = build_time_ranges(slots)

    assert [time_range.label for time_range in ranges] == ["8-10AM", "1-5PM"]


def test_build_time_ranges_preserves_half_hour_windows():
    slots = parse_available_slots(
        [
            "8:30 AM Court 1",
            "9:00 AM Court 1",
            "9:30 AM Court 1",
        ]
    )

    ranges = build_time_ranges(slots)

    assert [time_range.label for time_range in ranges] == ["8:30-10AM"]


def test_parse_time_range_text_handles_compact_courtreserve_labels():
    assert parse_time_range_text("8-10AM").label == "8-10AM"
    assert parse_time_range_text("12-6PM").label == "12-6PM"


def test_build_court_time_ranges_keeps_courts_separate():
    slots = parse_available_slots(
        [
            "Court 1 8:00 AM Maintenance",
            "Court 1 9:00 AM Available",
            "Court 1 10:00 AM Available",
            "Court 1 11:00 AM Available",
            "Court 1 12:00 PM Available",
            "Court 1 1:00 PM Available",
            "Court 1 2:00 PM Available",
            "Court 1 3:00 PM Available",
            "Court 1 4:00 PM Available",
            "Court 1 5:00 PM Available",
            "Court 2 8:00 AM Maintenance",
            "Court 2 9:00 AM Available",
            "Court 2 10:00 AM Available",
            "Court 2 11:00 AM Available",
            "Court 2 12:00 PM Available",
            "Court 2 1:00 PM Available",
            "Court 2 2:00 PM Available",
            "Court 2 3:00 PM Available",
            "Court 2 4:00 PM Available",
            "Court 2 5:00 PM Available",
        ]
    )

    ranges = build_court_time_ranges(slots)

    assert {court: [time_range.label for time_range in court_ranges] for court, court_ranges in ranges.items()} == {
        "Court 1": ["9AM-6PM"],
        "Court 2": ["9AM-6PM"],
    }


def test_build_available_time_ranges_subtracts_reservations_from_visible_window():
    ranges = build_available_time_ranges(
        TimeRange(start_minutes=8 * 60, end_minutes=19 * 60),
        [
            TimeRange(start_minutes=10 * 60, end_minutes=12 * 60),
            TimeRange(start_minutes=18 * 60, end_minutes=20 * 60),
        ],
    )

    assert [time_range.label for time_range in ranges] == ["8-10AM", "12-6PM"]


def test_build_court_ranges_from_schedule_snapshot_matches_april_7_2026_screenshot():
    snapshot = {
        "visibleStart": "8:00 AM",
        "visibleEnd": "12:00 AM",
        "slotDurationMinutes": 30,
        "courts": [
            {
                "name": "Pickleball Court #1 (Pickleball)",
                "reservations": [
                    "Pickleball Court Reservation 7:00 PM - 8:00 PM Thu Ngo, Stella Dao, Brianna Luong, Cecilia Lu",
                    "Pickleball Court Reservation 8:00 PM - 10:00 PM Kevin T. Nguyen",
                ],
            },
            {
                "name": "Pickleball Court #2 (Pickleball)",
                "reservations": [
                    "Pickleball Court Reservation 10:00 AM - 12:00 PM Steve Vu",
                    "Pickleball Court Reservation 6:00 PM - 8:00 PM Joyce Bui",
                    "Pickleball Court Reservation 8:00 PM - 9:00 PM Julie Hung",
                    "Pickleball Court Reservation 9:00 PM - 10:00 PM Julie Hung",
                ],
            },
        ],
    }

    ranges = build_court_ranges_from_schedule_snapshot(snapshot)

    assert {
        court: [time_range.label for time_range in court_ranges]
        for court, court_ranges in ranges.items()
    } == {
        "Pickleball Court #1 (Pickleball)": ["8AM-7PM", "10PM-12AM"],
        "Pickleball Court #2 (Pickleball)": ["8-10AM", "12-6PM", "10PM-12AM"],
    }
