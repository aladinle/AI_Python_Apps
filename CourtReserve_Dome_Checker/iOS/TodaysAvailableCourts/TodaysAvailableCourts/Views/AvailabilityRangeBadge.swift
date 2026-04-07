import SwiftUI

struct AvailabilityRangeBadge: View {
    let range: TimeRange

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)

            VStack(alignment: .leading, spacing: 4) {
                Text("\(range.startTime) - \(range.endTime)")
                    .font(.headline)
                    .foregroundStyle(.primary)

                Text("Available")
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            Spacer()
        }
        .padding(14)
        .background(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color.green.opacity(0.12))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.green.opacity(0.2), lineWidth: 1)
        )
    }
}

#Preview {
    AvailabilityRangeBadge(range: TimeRange(startTime: "8:00 AM", endTime: "10:00 AM"))
        .padding()
}
