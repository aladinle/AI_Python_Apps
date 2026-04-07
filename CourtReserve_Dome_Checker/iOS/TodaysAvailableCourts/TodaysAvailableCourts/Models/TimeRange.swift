import Foundation

struct TimeRange: Identifiable, Codable, Hashable {
    let startTime: String
    let endTime: String

    var id: String {
        "\(startTime)-\(endTime)"
    }
}
