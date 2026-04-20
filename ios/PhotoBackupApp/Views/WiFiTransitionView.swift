import SwiftUI

struct WiFiTransitionView: View {
    @Environment(AppState.self) private var appState
    @Environment(APIService.self) private var api
    let targetSSID: String
    var onDone: () -> Void

    @State private var elapsed: Int = 0
    @State private var reconnected: Bool = false
    @State private var probeTask: Task<Void, Never>?

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Image(systemName: reconnected ? "checkmark.circle.fill" : "wifi.exclamationmark")
                .font(.system(size: 72))
                .foregroundStyle(reconnected ? .phSuccess : .phWarning)
                .symbolEffect(.pulse, isActive: !reconnected)

            Text(reconnected ? "Conectat din nou!" : "Pi-ul se conectează la \(targetSSID)")
                .font(.title2.bold())
                .multilineTextAlignment(.center)
                .padding(.horizontal)

            if !reconnected {
                Text("Conectează și iPhone-ul la `\(targetSSID)`, apoi aștept să găsesc dispozitivul din nou...")
                    .multilineTextAlignment(.center)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                ProgressView()
                Text("Timp: \(elapsed)s")
                    .font(.caption.monospaced())
                    .foregroundStyle(.secondary)
            } else {
                Text("Dispozitivul răspunde la noua adresă.")
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Button(reconnected ? "Continuă" : "Anulează") {
                probeTask?.cancel()
                onDone()
            }
            .buttonStyle(.borderedProminent)
            .padding(.bottom)
        }
        .padding()
        .onAppear { start() }
        .onDisappear { probeTask?.cancel() }
    }

    private func start() {
        probeTask = Task {
            while !Task.isCancelled && !reconnected && elapsed < 120 {
                try? await Task.sleep(nanoseconds: 2_000_000_000)
                await MainActor.run { elapsed += 2 }
                // Încearcă mDNS și IP-ul curent
                let candidates: [URL] = [
                    Constants.mDNSBaseURL,
                    appState.settings.baseURL,
                ]
                if let url = await DeviceDiscovery.probe(candidates: candidates, timeout: 1.5) {
                    await MainActor.run {
                        api.setBaseURL(url)
                        appState.settings.baseURL = url
                        appState.settings.save()
                        reconnected = true
                    }
                    break
                }
            }
        }
    }
}
