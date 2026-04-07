import Foundation

protocol CourtAvailabilityProviding {
    func fetchTodayAvailability() -> [CourtAvailability]
}

struct MockCourtAvailabilityRepository: CourtAvailabilityProviding {
    func fetchTodayAvailability() -> [CourtAvailability] {
        let date = "Tuesday, April 7, 2026"

        return [
            CourtAvailability(
                courtName: "Pickleball Court #1",
                date: date,
                availableRanges: [
                    TimeRange(startTime: "8:00 AM", endTime: "7:00 PM")
                ]
            ),
            CourtAvailability(
                courtName: "Pickleball Court #2",
                date: date,
                availableRanges: [
                    TimeRange(startTime: "8:00 AM", endTime: "10:00 AM"),
                    TimeRange(startTime: "12:00 PM", endTime: "6:00 PM")
                ]
            )
        ]
    }
}
