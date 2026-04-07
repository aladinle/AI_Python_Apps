import Foundation

@MainActor
final class CourtAvailabilityViewModel: ObservableObject {
    @Published private(set) var courtAvailabilities: [CourtAvailability] = []
    @Published private(set) var lastUpdatedText: String?

    let title = "Today's Available Courts"
    let venueName = "The Dome"
    let viewName = "Lobby View"

    private let repository: CourtAvailabilityProviding

    init(repository: CourtAvailabilityProviding = MockCourtAvailabilityRepository()) {
        self.repository = repository
        refresh()
    }

    var displayDate: String {
        courtAvailabilities.first?.date ?? "Tuesday, April 7, 2026"
    }

    var isEmpty: Bool {
        courtAvailabilities.allSatisfy { $0.availableRanges.isEmpty }
    }

    func refresh() {
        courtAvailabilities = repository.fetchTodayAvailability()
        lastUpdatedText = Self.timestampFormatter.string(from: Date())
    }

    private static let timestampFormatter: DateFormatter = {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        formatter.dateStyle = .none
        return formatter
    }()
}
