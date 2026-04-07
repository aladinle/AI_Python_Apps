import SwiftUI

struct ContentView: View {
    @StateObject private var viewModel: CourtAvailabilityViewModel

    init(viewModel: CourtAvailabilityViewModel = CourtAvailabilityViewModel()) {
        _viewModel = StateObject(wrappedValue: viewModel)
    }

    var body: some View {
        NavigationStack {
            ZStack {
                LinearGradient(
                    colors: [
                        Color(.systemBackground),
                        Color.green.opacity(0.08),
                        Color(.secondarySystemBackground)
                    ],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        headerSection

                        if viewModel.isEmpty {
                            EmptyAvailabilityStateView()
                        } else {
                            ForEach(viewModel.courtAvailabilities) { availability in
                                CourtAvailabilityCard(availability: availability)
                            }
                        }
                    }
                    .padding(20)
                }
            }
            .navigationTitle(viewModel.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        viewModel.refresh()
                    } label: {
                        Label("Refresh", systemImage: "arrow.clockwise")
                    }
                }
            }
        }
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(viewModel.displayDate)
                .font(.title2.weight(.bold))
                .foregroundStyle(.primary)

            Text("\(viewModel.venueName) - \(viewModel.viewName)")
                .font(.subheadline)
                .foregroundStyle(.secondary)

            if let lastUpdatedText = viewModel.lastUpdatedText {
                Text("Last refreshed at \(lastUpdatedText)")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.bottom, 4)
    }
}

#Preview {
    ContentView()
}
