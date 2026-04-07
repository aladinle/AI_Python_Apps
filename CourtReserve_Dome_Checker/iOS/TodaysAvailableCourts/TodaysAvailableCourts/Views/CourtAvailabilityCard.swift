import SwiftUI

struct CourtAvailabilityCard: View {
    let availability: CourtAvailability

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text(availability.courtName)
                    .font(.title3.weight(.semibold))
                    .foregroundStyle(.primary)

                Text(availability.date)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }

            if availability.availableRanges.isEmpty {
                ContentUnavailableView(
                    "No available slots",
                    systemImage: "calendar.badge.exclamationmark",
                    description: Text("There are no open times for this court today.")
                )
                .frame(maxWidth: .infinity)
            } else {
                ForEach(availability.availableRanges) { range in
                    AvailabilityRangeBadge(range: range)
                }
            }
        }
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .fill(.regularMaterial)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 24, style: .continuous)
                .stroke(Color.primary.opacity(0.08), lineWidth: 1)
        )
        .shadow(color: Color.black.opacity(0.06), radius: 18, x: 0, y: 10)
    }
}

#Preview {
    CourtAvailabilityCard(
        availability: MockCourtAvailabilityRepository().fetchTodayAvailability()[0]
    )
    .padding()
    .background(Color(.systemGroupedBackground))
}
