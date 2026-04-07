import SwiftUI

struct EmptyAvailabilityStateView: View {
    var body: some View {
        ContentUnavailableView(
            "No courts available",
            systemImage: "calendar.badge.clock",
            description: Text("Check back later or refresh to load updated availability.")
        )
        .frame(maxWidth: .infinity)
        .padding(.vertical, 40)
    }
}

#Preview {
    EmptyAvailabilityStateView()
}
