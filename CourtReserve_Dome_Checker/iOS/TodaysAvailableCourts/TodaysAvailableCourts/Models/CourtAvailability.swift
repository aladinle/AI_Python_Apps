import Foundation

struct CourtAvailability: Identifiable, Codable, Hashable {
    let courtName: String
    let date: String
    let availableRanges: [TimeRange]

    var id: String {
        "\(courtName)-\(date)"
    }
}
